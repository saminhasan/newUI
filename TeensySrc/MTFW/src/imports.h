#ifndef IMPORTS_H
#define IMPORTS_H

#include <Arduino.h>
#include <RingBuffer.h>
# define USB_SERIAL_BUFFER_SIZE 512
# define PACKET_BUFFER_SIZE 8388608 // 8 MB
uint8_t serialBuffer[USB_SERIAL_BUFFER_SIZE];
EXTMEM uint8_t ringBuffer[PACKET_BUFFER_SIZE];
RingBuffer<uint8_t, PACKET_BUFFER_SIZE> packetBuffer(ringBuffer);
#endif // IMPORTS_H