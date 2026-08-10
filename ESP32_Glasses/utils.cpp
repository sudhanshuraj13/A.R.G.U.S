#include "utils.h"
#include "config.h"
void printSeparator() {
    Serial.println("----------------------------------------");
}

void printSystemStatus() {
    printSeparator();

    Serial.println("ESP32 SMART GLASSES");
    Serial.println();

    Serial.print("Wi-Fi SSID: ");
    Serial.println(WIFI_SSID);

    Serial.print("Pi Server: ");
    Serial.print(PI_SERVER_IP);
    Serial.print(":");
    Serial.println(PI_SERVER_PORT);

    Serial.print("Button 1 GPIO: ");
    Serial.println(BUTTON_1_PIN);

    Serial.print("Button 2 GPIO: ");
    Serial.println(BUTTON_2_PIN);

    Serial.print("Button 3 GPIO: ");
    Serial.println(BUTTON_3_PIN);

    Serial.print("Ultrasonic TRIG GPIO: ");
    Serial.println(ULTRASONIC_TRIG_PIN);

    Serial.print("Ultrasonic ECHO GPIO: ");
    Serial.println(ULTRASONIC_ECHO_PIN);

    printSeparator();
}

String detectionTypeToString(int detectionType) {
    switch (detectionType) {
        case 0:
            return "OBJECT";

        case 1:
            return "CURRENCY";

        case 2:
            return "AI";

        default:
            return "UNKNOWN";
    }
}
