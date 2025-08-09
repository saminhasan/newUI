#ifndef GLOBALS_H
#define GLOBALS_H
#include <stddef.h>
#include <stdint.h>
#include <Arduino.h>
#define Debug SerialUSB1
#define NODE_ID_MASTER 0x00
#define NODE_ID_PC 0xFF
#define NODE_ID NODE_ID_MASTER
static constexpr size_t SEND_BUFFER_SIZE     = 65536; // 64 KB = at 60 MB/s / 1ms
static constexpr size_t PACKET_OVERHEAD      = 16;
static constexpr size_t MAX_PACKET_SIZE      = size_t(8192*1000 + PACKET_OVERHEAD);               // 4 MB for the packet buffer
static constexpr size_t maxArrayLength       = size_t((MAX_PACKET_SIZE - PACKET_OVERHEAD)/ (6 * sizeof(float)));

EXTMEM uint8_t ringBufferArray[MAX_PACKET_SIZE];
typedef union {
    float data[maxArrayLength][6];            // Access as 2D float array
    uint8_t bytes[maxArrayLength * 6 * sizeof(float)]; // Access raw bytes
} DataBuffer;
EXTMEM DataBuffer dataBuffer;
DMAMEM uint8_t sendBuffer[SEND_BUFFER_SIZE];

#endif // GLOBALS_H