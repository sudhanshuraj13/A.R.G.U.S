#ifndef API_CLIENT_H
#define API_CLIENT_H

#include <Arduino.h>
#include "camera_manager.h"

enum DetectionType {
    DETECTION_OBJECT,
    DETECTION_CURRENCY,
    DETECTION_AI
};

class APIClient {
public:
    void begin();
    String getEndpoint(DetectionType type);
    bool sendImage(camera_fb_t* frame, DetectionType type);
    bool sendRequest(const uint8_t* imageData, size_t imageSize, const String& endpoint);
    bool sendDistance(float cm);
};

#endif
