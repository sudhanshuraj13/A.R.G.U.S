//#include <Arduino.h>
//#include "config.h"
//#include "wifi_manager.h"
//#include "camera_manager.h"
//#include "button_manager.h"
//#include "ultrasonic.h"
//#include "api_client.h"
//#include "utils.h"
//
//WiFiManager wifi;
//CameraManager cameraMgr;
//ButtonManager buttonMgr;
//UltrasonicSensor ultrasonic;
//APIClient apiClient;
//
//unsigned long lastUltrasonicCheck = 0;
//
//void setup() {
//    Serial.begin(SERIAL_BAUD_RATE);
//    delay(100);
//    Serial.println("ARGUS - ESP32-CAM starting");
//
//    wifi.begin();
//    apiClient.begin();
//
//    if (!cameraMgr.begin()) {
//        Serial.println("Camera init failed — check model and wiring.");
//    }
//
//    buttonMgr.begin();
//    ultrasonic.begin();
//
//    printSystemStatus();
//}
//
//void loop() {
//    wifi.maintainConnection();
//
//    ButtonAction act = buttonMgr.checkButtons();
//    if (act != BUTTON_NONE) {
//        Serial.printf("Button action: %d\n", act);
//        if (!cameraMgr.isReady()) {
//            Serial.println("Camera not ready — skipping capture");
//        } else {
//            camera_fb_t* fb = cameraMgr.capture();
//            if (!fb) {
//                Serial.println("Failed to capture frame");
//            } else {
//                DetectionType dt = DETECTION_OBJECT;
//                if (act == CURRENCY_DETECTION) dt = DETECTION_CURRENCY;
//                if (act == AI_ASSIST) dt = DETECTION_AI;
//
//                bool ok = apiClient.sendImage(fb, dt);
//                Serial.printf("sendImage result: %s\n", ok ? "OK" : "FAIL");
//                cameraMgr.release(fb);
//            }
//        }
//    }
//
//    // Ultrasonic periodic check
//    unsigned long now = millis();
//    if (now - lastUltrasonicCheck >= ULTRASONIC_INTERVAL_MS) {
//        lastUltrasonicCheck = now;
//        float d = ultrasonic.getDistanceCM();
//        if (d > 0) {
//            Serial.printf("Distance: %.2f cm\n", d);
//            if (ultrasonic.obstacleDetected()) {
//                Serial.println("Obstacle detected — sending distance to server");
//                apiClient.sendDistance(d);
//            }
//        }
//    }
//
//    delay(10);
//}


#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"

// ==========================
// Wi-Fi
// ==========================
const char* WIFI_SSID = "Poco M7 Pro";
const char* WIFI_PASSWORD = "gurkirat1234";

// ==========================
// AI Thinker ESP32-CAM
// ==========================
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

WebServer server(80);

// ==========================
// Home page
// ==========================
void handleRoot()
{
    String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>

<body>
    <h1>ESP32-CAM Server</h1>

    <p>
        <a href="/capture">
            <button>Capture Frame</button>
        </a>
    </p>
</body>
</html>
)rawliteral";

    server.send(200, "text/html", html);
}

// ==========================
// Capture frame
// ==========================
void handleCapture()
{
    camera_fb_t* frame = esp_camera_fb_get();

    if (frame == nullptr)
    {
        Serial.println("Camera capture failed");
        server.send(500, "text/plain", "Camera capture failed");
        return;
    }

    Serial.print("Captured frame: ");
    Serial.print(frame->len);
    Serial.println(" bytes");

    WiFiClient client = server.client();

    server.sendHeader("Content-Length", String(frame->len));
    server.send(200, "image/jpeg", "");

    client.write(frame->buf, frame->len);

    esp_camera_fb_return(frame);
}

// ==========================
// Camera initialization
// ==========================
bool initializeCamera()
{
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

    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;

    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;

    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound())
    {
        config.frame_size = FRAMESIZE_VGA;
        config.jpeg_quality = 10;
        config.fb_count = 2;
    }
    else
    {
        config.frame_size = FRAMESIZE_QVGA;
        config.jpeg_quality = 12;
        config.fb_count = 1;
    }

    esp_err_t result = esp_camera_init(&config);

    if (result != ESP_OK)
    {
        Serial.printf(
            "Camera initialization failed: 0x%x\n",
            result
        );

        return false;
    }

    Serial.println("Camera initialized successfully");

    return true;
}

// ==========================
// Wi-Fi initialization
// ==========================
void initializeWiFi()
{
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.print("Connecting to Wi-Fi");

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("Wi-Fi connected");

    Serial.print("ESP32-CAM IP: ");
    Serial.println(WiFi.localIP());
}

// ==========================
// Setup
// ==========================
void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("=========================");
    Serial.println("ESP32-CAM Starting");
    Serial.println("=========================");

    if (!initializeCamera())
    {
        Serial.println("Camera failed!");
        return;
    }

    initializeWiFi();

    server.on("/", HTTP_GET, handleRoot);
    server.on("/capture", HTTP_GET, handleCapture);

    server.begin();

    Serial.println("HTTP server started");
    Serial.println();
    Serial.println("Open this in your browser:");
    Serial.print("http://");
    Serial.println(WiFi.localIP());
}

// ==========================
// Main loop
// ==========================
void loop()
{
    server.handleClient();
}
