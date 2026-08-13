#ifndef CONFIG_H
#define CONFIG_H

// ======================================================
// ARGUS ESP32 SMART GLASSES - CONFIGURATION & TESTING SETUP
// ======================================================

// -------------------- Wi-Fi --------------------
// Change these to your Wi-Fi or Mobile Hotspot details.
// IMPORTANT: ESP32-CAM only supports 2.4 GHz Wi-Fi networks!
#define WIFI_SSID       "Poco M7 Pro"
#define WIFI_PASSWORD   "gurkirat1234"

// -------------------- Raspberry Pi Server --------------------
// Find the Raspberry Pi IP on your local Wi-Fi network using:
//   hostname -I
// Example: "192.168.1.50" or "10.28.160.146"
#define PI_SERVER_IP    "10.28.160.146"

// Port used by the Raspberry Pi FastAPI server
#define PI_SERVER_PORT  8000

// HTTP Timeout in milliseconds (increase if Llama Vision API takes longer)
#define HTTP_TIMEOUT_MS 15000

// -------------------- API Endpoints --------------------
#define OBJECT_ENDPOINT       "/detect/object"
#define CURRENCY_ENDPOINT     "/detect/currency"
#define ASSIST_ENDPOINT       "/assist"
#define LLAMA_VISION_ENDPOINT "/ai/scene"
#define AI_QUERY_ENDPOINT     "/ai/query"

// Active endpoint assigned to Button 3 (AI Scene Assistance)
#define AI_ENDPOINT           LLAMA_VISION_ENDPOINT

// -------------------- Buttons (GPIO Pins) --------------------
// Button 1 = Object Detection
// Button 2 = Currency Detection
// Button 3 = AI Vision Scene Description (Llama 3.2 Vision)
#define BUTTON_1_PIN  12
#define BUTTON_2_PIN  13
#define BUTTON_3_PIN  14

#define BUTTON_DEBOUNCE_MS  50

// -------------------- Ultrasonic Distance Sensor --------------------
#define ULTRASONIC_ENABLED      true
#define ULTRASONIC_TRIG_PIN     17
#define ULTRASONIC_ECHO_PIN     16

// Distance threshold in cm for obstacle alert
#define OBSTACLE_DISTANCE_CM    80

// How often to read the ultrasonic sensor (ms)
#define ULTRASONIC_INTERVAL_MS  300

// Minimum interval between sending obstacle warnings to Raspberry Pi (ms)
#define DISTANCE_SEND_INTERVAL_MS 1000

// -------------------- Camera (AI-Thinker ESP32-CAM) --------------------
#define CAMERA_MODEL_AI_THINKER

// JPEG Quality (10-63): Lower number = higher quality & larger image payload
// Quality 12 is optimal for YOLO detection & Llama Vision inference over Wi-Fi
#define CAMERA_JPEG_QUALITY 12

// Number of frame buffers
#define CAMERA_FB_COUNT 1

// -------------------- Debugging --------------------
#define SERIAL_BAUD_RATE 115200

#endif
