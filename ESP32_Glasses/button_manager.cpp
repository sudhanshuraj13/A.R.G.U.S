#include "button_manager.h"
#include "config.h"

ButtonManager::ButtonManager()
    : lastButton1State(HIGH),
      lastButton2State(HIGH),
      lastButton3State(HIGH),
      lastDebounceTime1(0),
      lastDebounceTime2(0),
      lastDebounceTime3(0) {
}

void ButtonManager::begin() {

    if (BUTTON_1_PIN >= 0) {
        pinMode(BUTTON_1_PIN, INPUT_PULLUP);
    }

    if (BUTTON_2_PIN >= 0) {
        pinMode(BUTTON_2_PIN, INPUT_PULLUP);
    }

    if (BUTTON_3_PIN >= 0) {
        pinMode(BUTTON_3_PIN, INPUT_PULLUP);
    }

    Serial.println("Button manager initialized.");
}


bool ButtonManager::buttonPressed(
    int pin,
    bool &lastState,
    unsigned long &lastDebounceTime
) {

    if (pin < 0) {
        return false;
    }

    bool currentState = digitalRead(pin);

    if (currentState != lastState) {
        lastDebounceTime = millis();
        lastState = currentState;
    }

    if ((millis() - lastDebounceTime) > BUTTON_DEBOUNCE_MS) {

        // INPUT_PULLUP means LOW = button pressed
        if (currentState == LOW) {
            return true;
        }
    }

    return false;
}


ButtonAction ButtonManager::checkButtons() {

    if (buttonPressed(
            BUTTON_1_PIN,
            lastButton1State,
            lastDebounceTime1
        )) {

        delay(200);
        return OBJECT_DETECTION;
    }

    if (buttonPressed(
            BUTTON_2_PIN,
            lastButton2State,
            lastDebounceTime2
        )) {

        delay(200);
        return CURRENCY_DETECTION;
    }

    if (buttonPressed(
            BUTTON_3_PIN,
            lastButton3State,
            lastDebounceTime3
        )) {

        delay(200);
        return AI_ASSIST;
    }

    return BUTTON_NONE;
}
