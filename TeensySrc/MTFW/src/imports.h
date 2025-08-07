#ifndef IMPORTS_H
#define IMPORTS_H

#include <Arduino.h>
#include <RingBuffer.h>
#include <FastCRC.h>
#include <MsgID.h>
static constexpr size_t UB_SIZE              = 512;
static constexpr size_t MB                   = 1024 * 1024;
static constexpr size_t MIN_PACKET_SIZE      = 16;
static constexpr size_t MAX_PACKET_SIZE      = size_t(7 * MB + MIN_PACKET_SIZE);               // 1 MB for the packet buffer
static constexpr size_t PACKET_BUFFER_SIZE   = MAX_PACKET_SIZE;      // 1 MB
static constexpr size_t maxArrayLength       = size_t((PACKET_BUFFER_SIZE - MIN_PACKET_SIZE)/ (6 * sizeof(float)));
uint32_t arrayLength = 0;

typedef union {
    float data[maxArrayLength][6];            // Access as 2D float array
    uint8_t bytes[maxArrayLength * 6 * sizeof(float)]; // Access raw bytes
} DataBuffer;
EXTMEM DataBuffer db;


// Packet information structure
struct PacketInfo {
    uint32_t packetLength;
    uint32_t sequenceNumber;
    uint8_t systemId;
    uint8_t axisId;
    uint32_t payloadSize;
    uint8_t msgID;
    uint32_t crc;
    bool isValid;
    PacketInfo() : packetLength(0), sequenceNumber(0), systemId(0), axisId(0), payloadSize(0), msgID(0), crc(0), isValid(false) {}
};
PacketInfo pktInfo;

// Global variables
EXTMEM uint8_t ringBuffer[PACKET_BUFFER_SIZE];
RingBuffer<uint8_t, PACKET_BUFFER_SIZE> packetBuffer(ringBuffer);
FastCRC32 CRC32;
uint32_t crc;



#endif // IMPORTS_H