#include "wifi_manager.h"
#include "config.h"

void WiFiManager::begin() {
    Serial.println();
    Serial.println("================================");
    Serial.println("Connecting to Wi-Fi...");
    Serial.println("================================");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;

    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Wi-Fi connected!");
        Serial.print("ESP32 IP: ");
        Serial.println(WiFi.localIP());
        Serial.print("Signal strength: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
    } else {
        Serial.println("ERROR: Could not connect to Wi-Fi.");
    }
}

bool WiFiManager::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

void WiFiManager::maintainConnection() {

    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    Serial.println("Wi-Fi connection lost.");
    Serial.println("Attempting to reconnect...");

    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;

    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Wi-Fi reconnected!");
        Serial.print("ESP32 IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("Reconnect failed.");
    }
}

String WiFiManager::getIPAddress() {

    if (WiFi.status() == WL_CONNECTED) {
        return WiFi.localIP().toString();
    }

    return "0.0.0.0";
}
