#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"

// ==================== CONFIGURATION SECTION ====================
// WiFi Settings
const char* WIFI_SSID = "EACCESS";
const char* WIFI_PASSWORD = "hostelnet";

// Static IP Configuration
bool USE_STATIC_IP = true;               // Set to false to use DHCP
IPAddress STATIC_IP(192, 168, 1, 100);   // Desired IP
IPAddress GATEWAY(192, 168, 1, 1);       // Router gateway
IPAddress SUBNET(255, 255, 255, 0);      // Subnet mask
IPAddress DNS1(8, 8, 8, 8);              // Primary DNS
IPAddress DNS2(8, 8, 4, 4);              // Secondary DNS

// Server Settings
const int HTTP_PORT = 80;                // Main web server port
const int STREAM_PORT = 81;              // Video stream port

// Camera Model (AI-Thinker is most common)
#define CAMERA_MODEL_AI_THINKER
// Pin definitions for AI-THINKER
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Camera Quality Settings
// Choose frame size based on PSRAM availability
#define FRAME_SIZE_VGA       // Options: FRAMESIZE_QQVGA, QVGA, VGA, SVGA, XGA, UXGA
#define JPEG_QUALITY        12  // 0-63 (lower = higher quality)

// ==================== END CONFIGURATION ====================

// ==================== GLOBAL OBJECTS ====================
WebServer server(HTTP_PORT);
WiFiServer streamServer(STREAM_PORT);

// ==================== CAMERA INITIALIZATION ====================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Set frame size and quality based on PSRAM
  if (psramFound()) {
    config.frame_size = FRAMESIZE_UXGA;   // 1600x1200
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA;    // 640x480
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }

  // Optional camera sensor adjustments
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);
  s->set_contrast(s, 0);
  s->set_saturation(s, 0);
  s->set_special_effect(s, 0);
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_aec2(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_hmirror(s, 0);
  s->set_vflip(s, 0);

  return true;
}

// ==================== HTML CONTENT SECTION ====================
// Root page HTML (embedded as PROGMEM string)
const char MAIN_PAGE[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32-CAM Server</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            max-width: 800px;
            width: 100%;
            margin: 20px 0;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        .demo-section {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        h2 {
            color: #555;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        video, img {
            width: 100%;
            max-width: 640px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            display: block;
            margin: 0 auto;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px;
            font-weight: bold;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
        }
        .button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .button-container {
            text-align: center;
            margin: 20px 0;
        }
        .info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
            color: #1976d2;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ESP32-CAM Server</h1>

        <div class="info">
            <strong>Server Information:</strong><br>
            IP Address: <span id="ip-address">Loading...</span><br>
            Stream URL: <span id="stream-url">Loading...</span>
        </div>

        <div class="demo-section">
            <h2>📹 Live Video Stream</h2>
            <video id="video-stream" autoplay playsinline></video>
            <div class="button-container">
                <button class="button" onclick="startStream()">Start Stream</button>
                <button class="button" onclick="stopStream()">Stop Stream</button>
            </div>
        </div>

        <div class="demo-section">
            <h2>📸 Image Capture</h2>
            <img id="captured-image" src="/capture" alt="Captured Image">
            <div class="button-container">
                <button class="button" onclick="captureImage()">Capture New Image</button>
                <a class="button" href="/capture" download="esp32-cam-photo.jpg">Download Photo</a>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('ip-address').textContent = window.location.hostname;
        document.getElementById('stream-url').textContent = 'http://' + window.location.host + ':81/stream';

        const videoElement = document.getElementById('video-stream');
        let streamActive = false;

        function startStream() {
            if (!streamActive) {
                videoElement.src = 'http://' + window.location.host + ':81/stream';
                videoElement.play();
                streamActive = true;
            }
        }

        function stopStream() {
            if (streamActive) {
                videoElement.src = '';
                streamActive = false;
            }
        }

        function captureImage() {
            document.getElementById('captured-image').src = '/capture?t=' + new Date().getTime();
        }

        // Auto-refresh image every 5 seconds
        setInterval(() => {
            if (document.visibilityState === 'visible') captureImage();
        }, 5000);
    </script>
</body>
</html>
)rawliteral";

// ==================== ROUTE HANDLERS ====================
// Handler for root page
void handleRoot() {
  server.send_P(200, "text/html", MAIN_PAGE);
}

// Handler for image capture
void handleCapture() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

// Handler for 404
void handleNotFound() {
  server.send(404, "text/plain", "Not Found");
}

// ==================== STREAMING SERVER ====================
void handleStreamClient() {
  WiFiClient client = streamServer.available();
  if (!client) return;

  Serial.println("New stream client connected");
  String currentLine = "";
  while (client.connected()) {
    if (client.available()) {
      char c = client.read();
      if (c == '\n') {
        if (currentLine.length() == 0) {
          // Send HTTP headers for MJPEG stream
          client.println("HTTP/1.1 200 OK");
          client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
          client.println();
          break;
        } else {
          currentLine = "";
        }
      } else if (c != '\r') {
        currentLine += c;
      }
    }
  }

  // Stream loop
  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
      delay(10);
      continue;
    }

    client.println("--frame");
    client.print("Content-Type: image/jpeg\r\n\r\n");
    client.write(fb->buf, fb->len);
    client.println();

    esp_camera_fb_return(fb);
    delay(100); // ~10 FPS
  }

  Serial.println("Stream client disconnected");
  client.stop();
}

// ==================== WIFI SETUP ====================
bool setupWiFi() {
  Serial.println("\nConnecting to WiFi...");

  // Configure static IP if enabled
  if (USE_STATIC_IP) {
    if (!WiFi.config(STATIC_IP, GATEWAY, SUBNET, DNS1, DNS2)) {
      Serial.println("Failed to configure static IP - falling back to DHCP");
    } else {
      Serial.print("Static IP configured: ");
      Serial.println(STATIC_IP);
    }
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWiFi connection failed!");
    return false;
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Gateway: ");
  Serial.println(WiFi.gatewayIP());
  Serial.print("Subnet: ");
  Serial.println(WiFi.subnetMask());
  return true;
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================");
  Serial.println("ESP32-CAM Server Starting...");
  Serial.println("========================================");

  // Initialize camera
  if (!initCamera()) {
    Serial.println("Camera initialization failed!");
    return;
  }
  Serial.println("Camera initialized successfully");

  // Setup WiFi
  if (!setupWiFi()) {
    Serial.println("WiFi setup failed!");
    return;
  }

  // Setup HTTP routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/capture", HTTP_GET, handleCapture);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("HTTP server started on port 80");

  // Start stream server
  streamServer.begin();
  Serial.println("Stream server started on port 81");

  Serial.println("\n========================================");
  Serial.println("Server ready! Access via:");
  Serial.print("  http://");
  Serial.println(WiFi.localIP());
  Serial.println("  Stream: http://" + WiFi.localIP().toString() + ":81/stream");
  Serial.println("========================================\n");
}

// ==================== MAIN LOOP ====================
void loop() {
  server.handleClient();
  handleStreamClient();
  delay(1);
}
