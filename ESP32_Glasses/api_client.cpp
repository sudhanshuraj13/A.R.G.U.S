#include "api_client.h"
#include "config.h"

#include <WiFi.h>
#include <HTTPClient.h>

void APIClient::begin() {
    // No initialization required yet.
}

String APIClient::getEndpoint(DetectionType type) {

    switch (type) {

        case DETECTION_OBJECT:
            return OBJECT_ENDPOINT;

        case DETECTION_CURRENCY:
            return CURRENCY_ENDPOINT;

        case DETECTION_AI:
            return AI_ENDPOINT;

        default:
            return "/";
    }
}


bool APIClient::sendImage(
    camera_fb_t* frame,
    DetectionType type
) {

    if (frame == nullptr) {
        Serial.println("API: No image available.");
        return false;
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("API: Wi-Fi not connected.");
        return false;
    }

    String endpoint = getEndpoint(type);

    return sendRequest(
        frame->buf,
        frame->len,
        endpoint
    );
}


bool APIClient::sendRequest(
    const uint8_t* imageData,
    size_t imageSize,
    const String& endpoint
) {

    String serverURL =
        "http://" +
        String(PI_SERVER_IP) +
        ":" +
        String(PI_SERVER_PORT) +
        endpoint;

    Serial.println();
    Serial.println("Sending image to Raspberry Pi...");
    Serial.println(serverURL);

    HTTPClient http;

    http.begin(serverURL);

    // Tell the Pi that we're sending JPEG data
    http.addHeader(
        "Content-Type",
        "image/jpeg"
    );

    http.setTimeout(15000);

    int responseCode = http.POST(
        const_cast<uint8_t*>(imageData),
        imageSize
    );

    if (responseCode > 0) {

        Serial.print("Pi response code: ");
        Serial.println(responseCode);

        String response = http.getString();

        Serial.println("Pi response:");
        Serial.println(response);

        http.end();

        return responseCode >= 200 &&
               responseCode < 300;
    }

    Serial.print("HTTP request failed: ");
    Serial.println(http.errorToString(responseCode));

    http.end();

    return false;
}


bool APIClient::sendDistance(float distance) {

    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }

    String serverURL =
        "http://" +
        String(PI_SERVER_IP) +
        ":" +
        String(PI_SERVER_PORT) +
        "/distance";

    HTTPClient http;

    http.begin(serverURL);

    http.addHeader(
        "Content-Type",
        "application/json"
    );

    String json = "{\"distance\":" +
                  String(distance, 2) +
                  "}";

    int responseCode = http.POST(json);

    if (responseCode > 0) {

        Serial.print("Distance response: ");
        Serial.println(responseCode);

        http.end();

        return responseCode >= 200 &&
               responseCode < 300;
    }

    http.end();

    return false;
}