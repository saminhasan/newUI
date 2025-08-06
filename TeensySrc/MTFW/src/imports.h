#ifndef IMPORTS_H
#define IMPORTS_H

#include <Arduino.h>
#include <RingBuffer.h>
#include <FastCRC.h>
// Packet constants
#define START_MARKER 0x01
#define END_MARKER 0x04
#define MIN_PACKET_SIZE 16

// Buffer sizes
#define USB_SERIAL_BUFFER_SIZE 512
#define PACKET_BUFFER_SIZE 8388608 // 8 MB

// Packet parsing state
enum class ParseState {
    WAITING_START,
    PACKET_FOUND,
    PACKET_ERROR
};

// Packet information structure
struct PacketInfo {
    uint32_t packetLength;
    uint32_t sequenceNumber;
    uint8_t systemId;
    uint8_t axisId;
    uint8_t msgID;
    uint32_t crc;
    bool isValid;
    PacketInfo() : packetLength(0), sequenceNumber(0), systemId(0), axisId(0), msgID(0), crc(0), isValid(false) {}
};

// Global variables
uint8_t serialBuffer[USB_SERIAL_BUFFER_SIZE];
EXTMEM uint8_t ringBuffer[PACKET_BUFFER_SIZE];
RingBuffer<uint8_t, PACKET_BUFFER_SIZE> packetBuffer(ringBuffer);
ParseState parseState = ParseState::WAITING_START;
PacketInfo pktInfo;
FastCRC32 CRC32;
uint32_t crc;
#endif // IMPORTS_H