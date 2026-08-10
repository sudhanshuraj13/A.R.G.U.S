#include "ultrasonic.h"
#include "config.h"

UltrasonicSensor::UltrasonicSensor() {}

void UltrasonicSensor::begin() {
    if (ULTRASONIC_TRIG_PIN >= 0) pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
    if (ULTRASONIC_ECHO_PIN >= 0) pinMode(ULTRASONIC_ECHO_PIN, INPUT);
}

float UltrasonicSensor::getDistanceCM() {
    if (ULTRASONIC_TRIG_PIN < 0 || ULTRASONIC_ECHO_PIN < 0) return -1.0;
    unsigned long now = millis();
    if (now - lastMeasurementTime < ULTRASONIC_INTERVAL_MS) return lastDistance;
    lastMeasurementTime = now;

    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

    unsigned long duration = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 30000UL);
    if (duration == 0) {
        lastDistance = -1.0;
    } else {
        lastDistance = (duration * 0.0343) / 2.0;
    }
    return lastDistance;
}

bool UltrasonicSensor::obstacleDetected() {
    float d = getDistanceCM();
    if (d < 0) return false;
    return d <= OBSTACLE_DISTANCE_CM;
}
