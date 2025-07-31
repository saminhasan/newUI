#include "imports.h"



void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  timer.begin(TimerCallback, 1000); // 1000us = 1ms
  while(!Serial.dtr())
    ;
}

void loop() {
  digitalWrite(LED_BUILTIN, Serial.dtr()); // Toggle the built-in LED
}

