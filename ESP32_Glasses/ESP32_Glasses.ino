/*
  =====================================================================
  ESP32-CAM Web Server: Stream + Capture + Demo Page
  =====================================================================
  Board:   AI-Thinker ESP32-CAM (change CAMERA MODEL section if different)

  Routes:
    /          -> HTML demo page (shows live stream + a "capture" button)
    /stream    -> MJPEG live video stream
    /capture   -> single JPEG snapshot

  File is split into clearly labeled sections so you can add / remove /
  edit any piece independently:
    1. USER CONFIG        <- edit WiFi creds + static IP here
    2. CAMERA PIN MAP      <- change only if you use a non-AI-Thinker board
    3. HTML PAGE           <- the page served at "/"
    4. HANDLER: /stream
    5. HANDLER: /capture
    6. HANDLER: /
    7. CAMERA INIT
    8. WIFI INIT
    9. SERVER START
    10. SETUP / LOOP

  Internet access note (read before deploying):
    This code by itself only serves on your LOCAL WiFi network using a
    static IP. To reach it from the internet you additionally need ONE
    of the following (outside this sketch, done on your router / cloud):
      a) Port forward your router's WAN port -> ESP32's static IP:80,
         then use yourPublicIP:PORT (get a free DDNS name if your IP
         changes, e.g. No-IP / DuckDNS), OR
      b) Use a reverse tunnel service (e.g. ngrok, Cloudflare Tunnel,
         Tailscale Funnel) running on a small always-on device pointed
         at the ESP32's local IP.
    Exposing an ESP32-CAM directly to the internet with no auth is a
    security risk (it has no HTTPS/auth here) — at minimum put it
    behind a VPN (Tailscale/WireGuard) rather than raw port-forwarding.
  =====================================================================
*/

#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "soc/soc.h"           // disable brownout detector
#include "soc/rtc_cntl_reg.h"  // disable brownout detector
#include <WiFi.h>

// =====================================================================
// 1. USER CONFIG  ------------------------------------------------------
// =====================================================================
#define WIFI_SSID       "Poco M7 Pro"
#define WIFI_PASSWORD   "gurkirat1234"

// Set to true for a fixed/static IP on your local network (recommended).
// Set to false to just use whatever IP your router assigns via DHCP.
#define USE_STATIC_IP   false

//IPAddress local_IP(192, 168, 1, 184);   // <- pick a free IP on your LAN
//IPAddress gateway(192, 168, 1, 1);      // <- your router's IP
//IPAddress subnet(255, 255, 255, 0);
//IPAddress primaryDNS(8, 8, 8, 8);
//IPAddress secondaryDNS(8, 8, 4, 4);
// Camera quality settings (tune for speed vs quality)
#define FRAME_SIZE      FRAMESIZE_VGA   // QVGA/CIF/VGA/SVGA/XGA/SXGA/UXGA
#define JPEG_QUALITY    12              // 0-63, lower = higher quality
#define FB_COUNT        2               // frame buffer count (needs PSRAM for >1)

// =====================================================================
// 2. CAMERA PIN MAP (AI-THINKER ESP32-CAM) ------------------------------
// =====================================================================
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

// Onboard flash LED (AI-Thinker) - optional, comment out block below to disable
#define FLASH_LED_PIN      4

// =====================================================================
// 3. HTML PAGE (served at "/") ------------------------------------------
// =====================================================================
static const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>ESP32-CAM</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial, sans-serif; text-align:center; background:#111; color:#eee; margin:0; padding:20px; }
    h1 { font-weight:600; }
    img, #snapshot { max-width:100%; border-radius:8px; border:2px solid #333; margin-top:10px; }
    button { background:#2d7ef7; color:#fff; border:none; padding:10px 18px; margin:8px; border-radius:6px; font-size:16px; cursor:pointer; }
    button:hover { background:#1d63d1; }
    .box { margin-bottom:30px; }
    a { color:#7fb2ff; }
  </style>
</head>
<body>
  <h1>ESP32-CAM Demo</h1>

  <div class="box">
    <h3>Live Stream (/stream)</h3>
    <img src="/stream" id="streamImg">
  </div>

  <div class="box">
    <h3>Single Capture (/capture)</h3>
    <button onclick="takeSnapshot()">Capture Image</button><br>
    <img id="snapshot" src="" style="display:none;">
  </div>

  <p>Direct links: <a href="/stream">/stream</a> | <a href="/capture">/capture</a></p>

  <script>
    function takeSnapshot() {
      const img = document.getElementById('snapshot');
      img.src = '/capture?_=' + new Date().getTime(); // cache-bust
      img.style.display = 'block';
    }
  </script>
</body>
</html>
)rawliteral";

// =====================================================================
// 4. HANDLER: /stream  (MJPEG multipart stream) --------------------------
// =====================================================================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char *STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  size_t jpg_buf_len = 0;
  uint8_t *jpg_buf = NULL;
  char part_buf[64];

  res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[stream] camera capture failed");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        bool ok = frame2jpg(fb, JPEG_QUALITY, &jpg_buf, &jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!ok) {
          Serial.println("[stream] JPEG conversion failed");
          res = ESP_FAIL;
        }
      } else {
        jpg_buf_len = fb->len;
        jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    }
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)jpg_buf, jpg_buf_len);
    }

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      jpg_buf = NULL;
    } else if (jpg_buf) {
      free(jpg_buf);
      jpg_buf = NULL;
    }

    if (res != ESP_OK) {
      Serial.println("[stream] client disconnected / send failed, ending stream");
      break;
    }
  }
  return res;
}

// =====================================================================
// 5. HANDLER: /capture  (single JPEG) ------------------------------------
// =====================================================================
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[capture] camera capture failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");

  esp_err_t res;
  if (fb->format == PIXFORMAT_JPEG) {
    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  } else {
    uint8_t *jpg_buf = NULL;
    size_t jpg_buf_len = 0;
    bool ok = frame2jpg(fb, JPEG_QUALITY, &jpg_buf, &jpg_buf_len);
    if (!ok) {
      esp_camera_fb_return(fb);
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    res = httpd_resp_send(req, (const char *)jpg_buf, jpg_buf_len);
    free(jpg_buf);
  }

  esp_camera_fb_return(fb);
  return res;
}

// =====================================================================
// 6. HANDLER: /  (demo page) --------------------------------------------
// =====================================================================
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, INDEX_HTML, strlen(INDEX_HTML));
}

// =====================================================================
// 7. CAMERA INIT ---------------------------------------------------------
// =====================================================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
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

  if (psramFound()) {
    config.frame_size = FRAME_SIZE;
    config.jpeg_quality = JPEG_QUALITY;
    config.fb_count = FB_COUNT;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[camera] init failed with error 0x%x\n", err);
    return false;
  }
  return true;
}

// =====================================================================
// 8. WIFI INIT -------------------------------------------------------------
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
    Serial.println("[wifi] failed to connect");
    return false;
  }

  Serial.print("[wifi] connected, IP address: ");
  Serial.println(WiFi.localIP());
  return true;
}

// =====================================================================
// 9. SERVER START ------------------------------------------------------
// =====================================================================
httpd_handle_t camera_httpd = NULL;

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;

  httpd_uri_t index_uri = {
    .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL
  };
  httpd_uri_t stream_uri = {
    .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL
  };
  httpd_uri_t capture_uri = {
    .uri = "/capture", .method = HTTP_GET, .handler = capture_handler, .user_ctx = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    Serial.println("[server] started successfully");
  } else {
    Serial.println("[server] failed to start");
  }
}

// =====================================================================
// 10. SETUP / LOOP -------------------------------------------------------
// =====================================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // disable brownout detector

  Serial.begin(115200);
  Serial.setDebugOutput(false);

#ifdef FLASH_LED_PIN
  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW); // off by default
#endif

  if (!initCamera()) {
    Serial.println("Halting: camera init failed. Check wiring / model.");
    while (true) delay(1000);
  }

  if (!initWiFi()) {
    Serial.println("Halting: WiFi connection failed. Check credentials.");
    while (true) delay(1000);
  }

  startCameraServer();

  Serial.print("Ready! Open: http://");
  Serial.println(WiFi.localIP());
  Serial.println("  /         -> demo page");
  Serial.println("  /stream   -> live MJPEG stream");
  Serial.println("  /capture  -> single JPEG snapshot");
}

void loop() {
  // Server runs in its own task; nothing needed here.
  delay(10000);
}