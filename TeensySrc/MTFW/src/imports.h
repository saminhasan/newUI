#ifndef IMPORTS_H
#define IMPORTS_H

#include <Arduino.h>
uint32_t counter = 0; // Global counter variable
IntervalTimer timer; // Timer for periodic tasks


void TimerCallback() {
    if(Serial.dtr())
    {
        // Serial.printf("%lu | %lu | %lu | %lu\n", counter, micros(), millis(), UINT32_MAX-counter);
        Serial.printf("%10lu | %10lu | %10lu | %10lu%*c\n",counter,micros(),millis(),UINT32_MAX - counter,462, ' ');
        counter++;
    }

}
#endif // IMPORTS_H