/*
  =====================================================================
  ARGUS ESP32 LiDAR Distance Sensor (TFmini Plus / TF-Luna)
  =====================================================================
  Board:   ESP32-WROOM-32 DevKit (30-pin)

  Sensor:  TFmini Plus / TF-Luna LiDAR (UART, 115200 baud)

  Wiring (ESP32 DevKit → TFmini Plus):
    VIN  (5V)    → Red wire   → LiDAR VCC  (power)
    GND          → Black wire → LiDAR GND  (ground)
    RX2  (GPIO16)→ Green wire → LiDAR TX   (ESP32 receives data)
    TX2  (GPIO17)→ White wire → LiDAR RX   (ESP32 sends commands)

  Audio / Buzzer / Vibration Alert:
    D4   (GPIO4) → Red wire   → Audio/Buzzer/Vibration (+)
    GND          → Blue wire  → Audio/Buzzer/Vibration (-)

  Routes:
    /            -> HTML live-distance dashboard
    /distance    -> JSON { "distance_cm", "strength", "temp_c", "ok", "audio_alert" }
    /health      -> simple health check

  Pinout reference (ESP32-WROOM-32 DevKit):
    Top row  : VIN GND D13 D12 D14 D27 D26 D25 D33 D32 D35 D34 VN VP EN
    Bottom row: 3V3 GND D15 D2  D4  RX2 TX2 D5  D18 D19 D21 RX0 TX0 D22 D23

  Sections:
    1. USER CONFIG
    2. PIN MAP (LiDAR + Audio)
    3. LIDAR GLOBALS & PROTOCOL
    4. HTML PAGE
    5. HANDLER: /distance
    6. HANDLER: /health
    7. HANDLER: /
    8. LIDAR & AUDIO LOGIC
    9. WIFI INIT
    10. SERVER START
    11. SETUP / LOOP
  =====================================================================
*/

#include "esp_http_server.h"
#include <WiFi.h>
#include <HardwareSerial.h>

// =====================================================================
// 1. USER CONFIG  -----------------------------------------------------
// =====================================================================
#define WIFI_SSID       "Poco M7 Pro"
#define WIFI_PASSWORD   "gurkirat1234"

// Set to true for a fixed/static IP on your local network.
// Set to false to use DHCP (router assigns IP automatically).
#define USE_STATIC_IP   false

// Uncomment and edit these if USE_STATIC_IP is true:
// IPAddress local_IP(192, 168, 1, 200);
// IPAddress gateway(192, 168, 1, 1);
// IPAddress subnet(255, 255, 255, 0);
// IPAddress primaryDNS(8, 8, 8, 8);
// IPAddress secondaryDNS(8, 8, 4, 4);

// Obstacle alert threshold (cm)
#define OBSTACLE_DISTANCE_CM    80
#define DANGER_DISTANCE_CM      30

// Audio / Buzzer / Vibration feedback
#define AUDIO_ENABLED           true

// How often to print distance to Serial (ms)
#define SERIAL_PRINT_INTERVAL   500

// =====================================================================
// 2. PIN MAP (ESP32-WROOM-32 DevKit) ----------------------------------
// =====================================================================
//
//  LiDAR uses UART2:
//    RX2 = GPIO 16  ← receives data FROM LiDAR TX (Green wire)
//    TX2 = GPIO 17  → sends commands TO LiDAR RX  (White wire)
//
#define LIDAR_RX_PIN    16    // ESP32 RX2 ← LiDAR TX (Green wire)
#define LIDAR_TX_PIN    17    // ESP32 TX2 → LiDAR RX (White wire)
#define LIDAR_BAUD      115200

// Audio / Buzzer output
//    D4  = GPIO 4   → Red wire (Blue wire is to GND)
#define AUDIO_PIN       4     // D4 (GPIO 4) Audio / Buzzer / Haptic

// Built-in LED for obstacle alert (GPIO 2)
#define LED_PIN         2

// =====================================================================
// 3. LIDAR GLOBALS & PROTOCOL ----------------------------------------
// =====================================================================
//
//  TFmini Plus / TF-Luna data frame (9 bytes):
//    [0] 0x59  - header
//    [1] 0x59  - header
//    [2] Dist_L
//    [3] Dist_H
//    [4] Strength_L
//    [5] Strength_H
//    [6] Temp_L      (TFmini Plus) or Reserved
//    [7] Temp_H      (TFmini Plus) or Reserved
//    [8] Checksum    (low 8 bits of sum of bytes 0-7)
//
//  Distance (cm) = Dist_H * 256 + Dist_L
//  Strength      = Strength_H * 256 + Strength_L
//  Temperature   = (Temp_H * 256 + Temp_L) / 8.0 - 256.0 °C
//

#define TFMINI_FRAME_SIZE   9
#define TFMINI_HEADER       0x59

HardwareSerial LidarSerial(2);   // UART2

// Latest readings (updated continuously in loop)
volatile int      lidar_distance_cm = -1;   // -1 = no valid reading
volatile int      lidar_strength    = 0;
volatile float    lidar_temp_c      = 0.0;
volatile bool     lidar_valid       = false;
volatile uint32_t lidar_read_count  = 0;
volatile uint32_t lidar_error_count = 0;

unsigned long lastSerialPrint = 0;

// =====================================================================
// 4. HTML PAGE (served at "/") ----------------------------------------
// =====================================================================
static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>ARGUS LiDAR & Audio Alert</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #0a0a1a;
      color: #eee;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
    }
    h1 { font-size: 1.6em; margin-bottom: 8px; color: #7fb2ff; }
    .subtitle { color: #888; font-size: 0.85em; margin-bottom: 24px; }

    .card {
      background: #161630;
      border: 1px solid #2a2a5a;
      border-radius: 16px;
      padding: 28px;
      margin: 10px 0;
      width: 100%;
      max-width: 420px;
      text-align: center;
    }

    .distance-value {
      font-size: 4em;
      font-weight: 700;
      color: #00ff88;
      line-height: 1.1;
      transition: color 0.3s;
    }
    .distance-unit { font-size: 0.35em; color: #888; font-weight: 400; }
    .distance-value.warning { color: #ffaa00; }
    .distance-value.danger  { color: #ff4444; }
    .distance-value.no-data { color: #555; }

    .bar-container {
      margin: 16px 0;
      background: #0d0d20;
      border-radius: 10px;
      height: 20px;
      overflow: hidden;
      border: 1px solid #2a2a5a;
    }
    .bar-fill {
      height: 100%;
      border-radius: 10px;
      transition: width 0.2s, background 0.3s;
      background: linear-gradient(90deg, #00ff88, #00cc66);
    }

    .stats { display: flex; justify-content: space-around; margin-top: 16px; }
    .stat { text-align: center; }
    .stat-label { font-size: 0.75em; color: #888; }
    .stat-value { font-size: 1.1em; font-weight: 600; color: #ccc; }

    .status-dot {
      display: inline-block;
      width: 10px; height: 10px;
      border-radius: 50%;
      background: #555;
      margin-right: 6px;
      vertical-align: middle;
    }
    .status-dot.ok { background: #00ff88; }
    .status-dot.err { background: #ff4444; }

    .info { color: #666; font-size: 0.8em; margin-top: 20px; }
    a { color: #7fb2ff; }
  </style>
</head>
<body>
  <h1>&#128065; ARGUS LiDAR & Audio Alert</h1>
  <p class="subtitle">Real-time distance measurement & haptic/audio alert</p>

  <div class="card">
    <div class="distance-value no-data" id="dist">---<span class="distance-unit"> cm</span></div>
    <div class="bar-container"><div class="bar-fill" id="bar" style="width:0%"></div></div>
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Strength</div>
        <div class="stat-value" id="str">---</div>
      </div>
      <div class="stat">
        <div class="stat-label">Temp</div>
        <div class="stat-value" id="tmp">---</div>
      </div>
      <div class="stat">
        <div class="stat-label">Audio Alert (D4)</div>
        <div class="stat-value" id="aud">OFF</div>
      </div>
    </div>
  </div>

  <div class="card">
    <p><span class="status-dot" id="dot"></span><span id="status">Connecting...</span></p>
  </div>

  <p class="info">
    API: <a href="/distance">/distance</a> (JSON) &nbsp;|&nbsp;
    <a href="/health">/health</a>
  </p>

  <script>
    const MAX_DIST = 1200;  // max display distance (cm)
    const WARN = 80;
    const DANGER = 30;

    async function poll() {
      try {
        const r = await fetch('/distance');
        const d = await r.json();

        const el = document.getElementById('dist');
        const bar = document.getElementById('bar');
        const dot = document.getElementById('dot');
        const st = document.getElementById('status');
        const aud = document.getElementById('aud');

        if (d.ok) {
          const cm = d.distance_cm;
          el.innerHTML = cm + '<span class="distance-unit"> cm</span>';
          el.className = 'distance-value' + (cm <= DANGER ? ' danger' : cm <= WARN ? ' warning' : '');

          const pct = Math.min(100, (cm / MAX_DIST) * 100);
          bar.style.width = pct + '%';
          bar.style.background = cm <= DANGER
            ? 'linear-gradient(90deg, #ff4444, #cc0000)'
            : cm <= WARN
            ? 'linear-gradient(90deg, #ffaa00, #cc8800)'
            : 'linear-gradient(90deg, #00ff88, #00cc66)';

          document.getElementById('str').textContent = d.strength;
          document.getElementById('tmp').textContent = d.temp_c.toFixed(1) + ' °C';

          if (d.audio_alert) {
            aud.textContent = 'ACTIVE';
            aud.style.color = '#ff4444';
          } else {
            aud.textContent = 'OFF';
            aud.style.color = '#888';
          }

          dot.className = 'status-dot ok';
          st.textContent = cm <= DANGER ? 'OBSTACLE - CRITICAL PROXIMITY!' : cm <= WARN ? 'Obstacle detected' : 'Path clear';
        } else {
          el.innerHTML = '---<span class="distance-unit"> cm</span>';
          el.className = 'distance-value no-data';
          bar.style.width = '0%';
          dot.className = 'status-dot err';
          st.textContent = 'No valid reading';
          aud.textContent = 'OFF';
          aud.style.color = '#888';
        }
      } catch (e) {
        document.getElementById('dot').className = 'status-dot err';
        document.getElementById('status').textContent = 'Connection lost';
      }
    }

    setInterval(poll, 150);
    poll();
  </script>
</body>
</html>
)rawliteral";

// =====================================================================
// 5. HANDLER: /distance  (JSON) --------------------------------------
// =====================================================================
static esp_err_t distance_handler(httpd_req_t *req) {
  bool alert_active = (lidar_valid && lidar_distance_cm > 0 && lidar_distance_cm <= OBSTACLE_DISTANCE_CM);

  char json[220];
  snprintf(json, sizeof(json),
    "{\"distance_cm\":%d,\"strength\":%d,\"temp_c\":%.1f,"
    "\"ok\":%s,\"audio_alert\":%s,\"reads\":%lu,\"errors\":%lu}",
    lidar_distance_cm,
    lidar_strength,
    lidar_temp_c,
    lidar_valid ? "true" : "false",
    alert_active ? "true" : "false",
    (unsigned long)lidar_read_count,
    (unsigned long)lidar_error_count
  );

  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, json, strlen(json));
}

// =====================================================================
// 6. HANDLER: /health  ------------------------------------------------
// =====================================================================
static esp_err_t health_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/plain");
  return httpd_resp_send(req, "OK", 2);
}

// =====================================================================
// 7. HANDLER: /  (dashboard page) ------------------------------------
// =====================================================================
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

// =====================================================================
// 8. LIDAR READ & AUDIO LOGIC -----------------------------------------
// =====================================================================

// Non-blocking Audio / Buzzer / Vibration Alert
// Pulses faster as obstacle gets closer; continuous when critically close.
unsigned long lastAudioToggleTime = 0;
bool audioPinState = false;

void updateAudioAlert() {
  if (!AUDIO_ENABLED) {
    digitalWrite(AUDIO_PIN, LOW);
    return;
  }

  if (lidar_valid && lidar_distance_cm > 0 && lidar_distance_cm <= OBSTACLE_DISTANCE_CM) {
    unsigned long now = millis();

    if (lidar_distance_cm <= DANGER_DISTANCE_CM) {
      // Critical proximity (<= 30 cm): continuous tone / vibration
      digitalWrite(AUDIO_PIN, HIGH);
      audioPinState = true;
    } else {
      // Proportional pulsing: 30cm -> 80ms interval, 80cm -> 350ms interval
      unsigned long interval = map(lidar_distance_cm, DANGER_DISTANCE_CM, OBSTACLE_DISTANCE_CM, 80, 350);

      if (now - lastAudioToggleTime >= interval) {
        lastAudioToggleTime = now;
        audioPinState = !audioPinState;
        digitalWrite(AUDIO_PIN, audioPinState ? HIGH : LOW);
      }
    }
  } else {
    // No obstacle within range
    if (audioPinState) {
      audioPinState = false;
      digitalWrite(AUDIO_PIN, LOW);
    }
  }
}

// Read TFmini Plus UART frames (non-blocking)
void readLidar() {
  static uint8_t buf[TFMINI_FRAME_SIZE];
  static uint8_t idx = 0;

  while (LidarSerial.available()) {
    uint8_t byte_in = LidarSerial.read();

    // --- State machine: look for 0x59 0x59 header ---
    if (idx == 0) {
      if (byte_in == TFMINI_HEADER) {
        buf[0] = byte_in;
        idx = 1;
      }
      continue;
    }

    if (idx == 1) {
      if (byte_in == TFMINI_HEADER) {
        buf[1] = byte_in;
        idx = 2;
      } else {
        idx = 0;   // not a valid header, reset
      }
      continue;
    }

    // --- Collect remaining bytes ---
    buf[idx] = byte_in;
    idx++;

    if (idx < TFMINI_FRAME_SIZE) {
      continue;   // frame not complete yet
    }

    // --- Full frame received, validate checksum ---
    idx = 0;  // reset for next frame

    uint8_t checksum = 0;
    for (int i = 0; i < TFMINI_FRAME_SIZE - 1; i++) {
      checksum += buf[i];
    }

    if (checksum != buf[TFMINI_FRAME_SIZE - 1]) {
      lidar_error_count++;
      continue;   // bad checksum, discard
    }

    // --- Parse valid frame ---
    int dist     = buf[2] | (buf[3] << 8);
    int strength = buf[4] | (buf[5] << 8);
    int raw_temp = buf[6] | (buf[7] << 8);
    float temp_c = (raw_temp / 8.0) - 256.0;

    // Sanity check: TFmini reports 0 or -1 for out-of-range
    if (dist > 0 && dist < 12000 && strength > 0) {
      lidar_distance_cm = dist;
      lidar_strength    = strength;
      lidar_temp_c      = temp_c;
      lidar_valid       = true;
    } else {
      lidar_valid = false;
    }

    lidar_read_count++;
  }
}

// =====================================================================
// 9. WIFI INIT --------------------------------------------------------
// =====================================================================
bool initWiFi() {
#if USE_STATIC_IP
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("[wifi] static IP configuration failed");
  }
#endif

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[wifi] connecting");

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 40) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] FAILED to connect!");
    return false;
  }

  Serial.print("[wifi] connected, IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

// =====================================================================
// 10. SERVER START ----------------------------------------------------
// =====================================================================
httpd_handle_t lidar_httpd = NULL;

void startLidarServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;

  httpd_uri_t index_uri = {
    .uri = "/", .method = HTTP_GET,
    .handler = index_handler, .user_ctx = NULL
  };
  httpd_uri_t distance_uri = {
    .uri = "/distance", .method = HTTP_GET,
    .handler = distance_handler, .user_ctx = NULL
  };
  httpd_uri_t health_uri = {
    .uri = "/health", .method = HTTP_GET,
    .handler = health_handler, .user_ctx = NULL
  };

  if (httpd_start(&lidar_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(lidar_httpd, &index_uri);
    httpd_register_uri_handler(lidar_httpd, &distance_uri);
    httpd_register_uri_handler(lidar_httpd, &health_uri);
    Serial.println("[server] started on port 80");
  } else {
    Serial.println("[server] FAILED to start");
  }
}

// =====================================================================
// 11. SETUP / LOOP ----------------------------------------------------
// =====================================================================
void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("======================================");
  Serial.println("   ARGUS LIDAR + AUDIO ALERT");
  Serial.println("   TFmini Plus / TF-Luna");
  Serial.println("======================================");
  Serial.println();

  // LED & Audio/Buzzer output setup
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  pinMode(AUDIO_PIN, OUTPUT);
  digitalWrite(AUDIO_PIN, LOW);

  // Quick power-on audio test beep (100ms)
  digitalWrite(AUDIO_PIN, HIGH);
  delay(100);
  digitalWrite(AUDIO_PIN, LOW);

  // Initialize UART2 for LiDAR
  //   LidarSerial.begin(baud, config, RX_pin, TX_pin)
  LidarSerial.begin(LIDAR_BAUD, SERIAL_8N1, LIDAR_RX_PIN, LIDAR_TX_PIN);
  Serial.println("[lidar] UART2 initialized");
  Serial.printf("[lidar] RX pin: GPIO %d (← LiDAR TX - Green wire)\n", LIDAR_RX_PIN);
  Serial.printf("[lidar] TX pin: GPIO %d (→ LiDAR RX - White wire)\n", LIDAR_TX_PIN);
  Serial.printf("[lidar] Baud: %d\n", LIDAR_BAUD);
  Serial.printf("[audio] Alert pin: GPIO %d (D4 - Red wire, GND - Blue wire)\n", AUDIO_PIN);
  Serial.println();

  // Connect to WiFi
  if (!initWiFi()) {
    Serial.println("Halting: WiFi connection failed. Check credentials.");
    while (true) delay(1000);
  }

  // Start HTTP server
  startLidarServer();

  Serial.println();
  Serial.print("Ready! Open: http://");
  Serial.println(WiFi.localIP());
  Serial.println("  /          -> live distance dashboard");
  Serial.println("  /distance  -> JSON distance data");
  Serial.println("  /health    -> health check");
  Serial.println();
}

void loop() {
  // 1. Read LiDAR data (non-blocking UART)
  readLidar();

  // 2. Audio/Buzzer alert (proportional pulsing rate based on distance)
  updateAudioAlert();

  // 3. Obstacle alert LED (GPIO 2)
  if (lidar_valid && lidar_distance_cm <= OBSTACLE_DISTANCE_CM && lidar_distance_cm > 0) {
    digitalWrite(LED_PIN, HIGH);
  } else {
    digitalWrite(LED_PIN, LOW);
  }

  // 4. Periodic Serial output
  unsigned long now = millis();
  if (now - lastSerialPrint >= SERIAL_PRINT_INTERVAL) {
    lastSerialPrint = now;

    if (lidar_valid) {
      Serial.printf("[LIDAR] Distance: %d cm | Strength: %d | Temp: %.1f °C",
                    lidar_distance_cm, lidar_strength, lidar_temp_c);

      if (lidar_distance_cm <= DANGER_DISTANCE_CM) {
        Serial.print("  *** CRITICAL DANGER ***");
      } else if (lidar_distance_cm <= OBSTACLE_DISTANCE_CM) {
        Serial.print("  *** OBSTACLE WARNING ***");
      }
      Serial.println();
    } else {
      Serial.println("[LIDAR] Waiting for valid data...");
    }
  }
}
