#ifndef GLOBALS_H
#define GLOBALS_H
#include <stddef.h>
#include <stdint.h>
#include <Arduino.h>
#define Debug SerialUSB1

static constexpr size_t UB_SIZE              = 512;
static constexpr size_t MB                   = 1024 * 1024;
static constexpr size_t MIN_PACKET_SIZE      = 16;
static constexpr size_t MAX_PACKET_SIZE      = size_t(7 * MB + MIN_PACKET_SIZE);               // 1 MB for the packet buffer
static constexpr size_t PACKET_BUFFER_SIZE   = MAX_PACKET_SIZE;      // 1 MB
static constexpr size_t maxArrayLength       = size_t((PACKET_BUFFER_SIZE - MIN_PACKET_SIZE)/ (6 * sizeof(float)));
typedef union {
    float data[maxArrayLength][6];            // Access as 2D float array
    uint8_t bytes[maxArrayLength * 6 * sizeof(float)]; // Access raw bytes
} DataBuffer;
EXTMEM uint8_t ringBufferArray[PACKET_BUFFER_SIZE];
EXTMEM DataBuffer dataBuffer;


#endif // GLOBALS_H