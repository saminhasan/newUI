#include "imports.h"



void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  timer.begin(TimerCallback, 100); // 100us = 0.1 ms
  while(!Serial.dtr())
    ;
}

void loop() {
  digitalWrite(LED_BUILTIN, Serial.dtr()); // Toggle the built-in LED
}

