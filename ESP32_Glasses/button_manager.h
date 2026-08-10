#ifndef BUTTON_MANAGER_H
#define BUTTON_MANAGER_H

#include <Arduino.h>

enum ButtonAction {
    BUTTON_NONE,
    OBJECT_DETECTION,
    CURRENCY_DETECTION,
    AI_ASSIST
};

class ButtonManager {
public:
    ButtonManager();

    void begin();
    ButtonAction checkButtons();

private:
    bool lastButton1State;
    bool lastButton2State;
    bool lastButton3State;
    unsigned long lastDebounceTime1;
    unsigned long lastDebounceTime2;
    unsigned long lastDebounceTime3;

    bool buttonPressed(int pin, bool &lastState, unsigned long &lastDebounceTime);
};

#endif
