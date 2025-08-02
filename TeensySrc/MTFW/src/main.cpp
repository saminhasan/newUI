#include "imports.h"



void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  timer.begin(TimerCallback, 1000); // 10000us = 10 ms
  while(!Serial.dtr())
    ;
}

void loop() {
  digitalWrite(LED_BUILTIN, Serial.dtr()); // Toggle the built-in LED
}

