#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>

class WiFiManager {
public:
    void begin();
    bool isConnected();
    void maintainConnection();
    String getIPAddress();
};

#endif
