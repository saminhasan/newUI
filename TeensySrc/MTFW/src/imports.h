#ifndef IMPORTS_H
#define IMPORTS_H

#include <Arduino.h>

IntervalTimer timer; // Timer for periodic tasks


void TimerCallback() {
    if(Serial.dtr())
    {
        Serial.printf("%lu\n", micros());
    }

}
#endif // IMPORTS_H