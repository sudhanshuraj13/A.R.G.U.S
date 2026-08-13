#include <Arduino.h>
#include "config.h"
#include "wifi_manager.h"
#include "camera_manager.h"
#include "button_manager.h"
#include "ultrasonic.h"
#include "api_client.h"
#include "utils.h"

WiFiManager wifi;
CameraManager cameraMgr;
ButtonManager buttonMgr;
UltrasonicSensor ultrasonic;
APIClient apiClient;

unsigned long lastUltrasonicCheck = 0;

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(100);
    Serial.println("ARGUS - ESP32-CAM starting");

    wifi.begin();
    apiClient.begin();

    if (!cameraMgr.begin()) {
        Serial.println("Camera init failed — check model and wiring.");
    }

    buttonMgr.begin();
    ultrasonic.begin();

    printSystemStatus();
}

void loop() {
    wifi.maintainConnection();

    ButtonAction act = buttonMgr.checkButtons();
    if (act != BUTTON_NONE) {
        Serial.printf("Button action: %d\n", act);
        if (!cameraMgr.isReady()) {
            Serial.println("Camera not ready — skipping capture");
        } else {
            camera_fb_t* fb = cameraMgr.capture();
            if (!fb) {
                Serial.println("Failed to capture frame");
            } else {
                DetectionType dt = DETECTION_OBJECT;
                if (act == CURRENCY_DETECTION) dt = DETECTION_CURRENCY;
                if (act == AI_ASSIST) dt = DETECTION_AI;

                bool ok = apiClient.sendImage(fb, dt);
                Serial.printf("sendImage result: %s\n", ok ? "OK" : "FAIL");
                cameraMgr.release(fb);
            }
        }
    }

    // Ultrasonic periodic check
    unsigned long now = millis();
    if (now - lastUltrasonicCheck >= ULTRASONIC_INTERVAL_MS) {
        lastUltrasonicCheck = now;
        float d = ultrasonic.getDistanceCM();
        if (d > 0) {
            Serial.printf("Distance: %.2f cm\n", d);
            if (ultrasonic.obstacleDetected()) {
                Serial.println("Obstacle detected — sending distance to server");
                apiClient.sendDistance(d);
            }
        }
    }

    delay(10);
}
