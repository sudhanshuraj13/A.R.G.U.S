#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include <Arduino.h>

class UltrasonicSensor {
public:
    UltrasonicSensor();

    void begin();

    float getDistanceCM();

    bool obstacleDetected();

private:
    unsigned long lastMeasurementTime;
    float lastDistance;
};

#endif
