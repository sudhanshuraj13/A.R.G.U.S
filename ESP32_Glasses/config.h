#ifndef CONFIG_H
#define CONFIG_H

// ======================================================
// ESP32 SMART GLASSES - CONFIGURATION
// ======================================================

// -------------------- Wi-Fi --------------------
// Change these to your Wi-Fi/hotspot details.
#define WIFI_SSID       "Poco M7 Pro"
#define WIFI_PASSWORD   "gurkirat1234"

// -------------------- Raspberry Pi --------------------
// Find the Pi's IP using:
// hostname -I
#define PI_SERVER_IP    "10.28.160.146"

// Port used by the Raspberry Pi server
#define PI_SERVER_PORT  8000

// -------------------- API Endpoints --------------------
#define OBJECT_ENDPOINT   "/detect/object"
#define CURRENCY_ENDPOINT "/detect/currency"
#define AI_ENDPOINT       "/assist"

// -------------------- Buttons --------------------
// IMPORTANT:
// Replace -1 with the actual GPIO numbers later.
//
// Button 1 = Object detection
// Button 2 = Currency detection
// Button 3 = AI / scene assistance

#define BUTTON_1_PIN  12
#define BUTTON_2_PIN  13
#define BUTTON_3_PIN  14

// -------------------- Ultrasonic Sensor --------------------
// Replace these once you know the GPIOs.

#define ULTRASONIC_TRIG_PIN  17
#define ULTRASONIC_ECHO_PIN  16

// Distance at which an obstacle warning should occur
#define OBSTACLE_DISTANCE_CM  80

// How often to check the ultrasonic sensor
#define ULTRASONIC_INTERVAL_MS  200

// -------------------- Camera --------------------
// This is for the common AI-Thinker ESP32-CAM.
//
// We'll verify the exact camera board when we initialize it.

#define CAMERA_MODEL_AI_THINKER

// -------------------- Button Settings --------------------

#define BUTTON_DEBOUNCE_MS  50

// -------------------- Serial Debugging --------------------

#define SERIAL_BAUD_RATE 115200

// -------------------- Image Settings --------------------

#define CAMERA_JPEG_QUALITY 12

// Number of frame buffers
#define CAMERA_FB_COUNT 1

#endif
