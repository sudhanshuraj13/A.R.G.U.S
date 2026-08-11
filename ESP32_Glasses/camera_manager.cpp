#include "camera_manager.h"
#include "config.h"
#include <esp_camera.h>

bool CameraManager::begin() {
#ifdef CAMERA_MODEL_AI_THINKER
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = 5;
    config.pin_d1 = 18;
    config.pin_d2 = 19;
    config.pin_d3 = 21;
    config.pin_d4 = 36;
    config.pin_d5 = 39;
    config.pin_d6 = 34;
    config.pin_d7 = 35;
    config.pin_xclk = 0;
    config.pin_pclk = 22;
    config.pin_vsync = 25;
    config.pin_href = 23;
    config.pin_sscb_sda = 26;
    config.pin_sscb_scl = 27;
    config.pin_pwdn = 32;
    config.pin_reset = -1;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;
    config.fb_count = CAMERA_FB_COUNT;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        initialized = false;
        return false;
    }
    initialized = true;
    return true;
#else
    Serial.println("Camera model not defined in config.h");
    initialized = false;
    return false;
#endif
}

camera_fb_t* CameraManager::capture() {
    if (!initialized) return nullptr;
    camera_fb_t* fb = esp_camera_fb_get();
    return fb;
}

void CameraManager::release(camera_fb_t* frame) {
    if (frame) esp_camera_fb_return(frame);
}

bool CameraManager::isReady() { return initialized; }
