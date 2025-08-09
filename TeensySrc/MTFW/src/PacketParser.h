#ifndef PACKET_PARSER_H
#define PACKET_PARSER_H

#include <globals.h>
#include <RingBuffer.h>
#include <FastCRC.h>
#include <messages.h>

void printArray(float arr[][6], size_t length)
{
    for (size_t i = length - 1; i < length; i++)
    {
        Debug.printf("%zu : %f %f %f %f %f %f\n", i + 1, arr[i][0], arr[i][1], arr[i][2], arr[i][3], arr[i][4], arr[i][5]);
    }
}
enum class ParseState
{
    AWAIT_START,
    AWAIT_HEADER,
    AWAIT_PAYLOAD,
    PACKET_FOUND,
    PACKET_HANDLING,
    PACKET_ERROR
};
static const char *stateNames[] = {
    "AWAIT_START", "AWAIT_HEADER", "AWAIT_PAYLOAD",
    "PACKET_FOUND", "PACKET_HANDLING", "PACKET_ERROR"};
// Packet information structure
struct PacketInfo
{
    union
    {
        struct __attribute__((packed))
        {
            uint32_t packetLength;
            uint32_t sequenceNumber;
            uint8_t fromID; // from
            uint8_t toID; // to
            uint32_t crc;
        };
        uint8_t headerBytes[14];
    };

    uint32_t payloadSize;
    uint8_t msgID;
    uint8_t isValid;
};
template <size_t bufferSize>// Forward declaration
class Parser;
template <size_t bufferSize> // Callback function type - takes a reference to the parser
using PacketCallback = void (*)(Parser<bufferSize> &parser);

template <size_t bufferSize>
class Parser
{
public:
    uint32_t crc;
    FastCRC32 CRC32;
    PacketInfo pktInfo;
    RingBuffer<uint8_t, bufferSize> packetBuffer;
    ParseState parseState = ParseState::AWAIT_START;
    ParseState lastState = ParseState::AWAIT_START;
    PacketCallback<bufferSize> callback;
    uint32_t stateStartTime = 0;
    Parser(uint8_t *externalBuffer, PacketCallback<bufferSize> cb = nullptr)
        : packetBuffer(externalBuffer), callback(cb) {};

    void debugInfo()
    {
        if (lastState != parseState)
        {
            if (lastState != ParseState::AWAIT_START || stateStartTime != 0)
            {
                uint32_t timeSpent = micros() - stateStartTime;
                Debug.printf("%s took %lu μs\n", stateNames[static_cast<int>(lastState)], timeSpent);
            }
            lastState = parseState;
            stateStartTime = micros();
        }
    }
    void parse()
    {
        // debugInfo();
        switch (parseState)
        {
        case ParseState::AWAIT_START:
            if (packetBuffer.popUntil(START_MARKER))
            {
                parseState = ParseState::AWAIT_HEADER;
            }
            break;

        case ParseState::AWAIT_HEADER:
            if (packetBuffer.size() >= 14)
            {
                packetBuffer.readBytes(pktInfo.headerBytes, 14);
                crc = CRC32.crc32(pktInfo.headerBytes, 10);
                pktInfo.payloadSize = pktInfo.packetLength - PACKET_OVERHEAD;
                if (pktInfo.payloadSize > (MAX_PACKET_SIZE - PACKET_OVERHEAD) || pktInfo.payloadSize < 0)
                {
                    Debug.printf("Invalid packet size: %lu\n", pktInfo.payloadSize);
                    parseState = ParseState::PACKET_ERROR;
                }
                else
                {
                    parseState = ParseState::AWAIT_PAYLOAD;
                }
            }
            break;

        case ParseState::AWAIT_PAYLOAD:
            if (packetBuffer.size() >= (pktInfo.payloadSize + 1))
                parseState = ParseState::PACKET_FOUND;
            break;

        case ParseState::PACKET_FOUND:
        {
            for (size_t i = 0; i < pktInfo.payloadSize; i++)
            {   uint8_t b = packetBuffer[i];
                crc = CRC32.crc32_upd(&b, 1);
            }
            pktInfo.isValid = (crc == pktInfo.crc) && (packetBuffer[pktInfo.payloadSize] == END_MARKER);
            if (pktInfo.isValid)
            {
                packetBuffer.pop(pktInfo.msgID);
                parseState = ParseState::PACKET_HANDLING;
            }
            else
            {
                if (!(packetBuffer[pktInfo.payloadSize] == END_MARKER))
                    Debug.printf(" Invalid End marker  (expected: 0x%02X, found: 0x%02X)\n", END_MARKER, packetBuffer[pktInfo.payloadSize]);
                else if (!(crc == pktInfo.crc))
                    Debug.printf(" Invalid CRC  (expected: 0x%08X, computed: 0x%08X)\n", pktInfo.crc, crc);
                else
                    Debug.printf("Unknown error\n");
                Debug.printf("Packet Info: len=%u, size=%u, seq=%u, from=%u, to=%u, msgID=0x%02X\n",
                    pktInfo.packetLength, pktInfo.payloadSize, pktInfo.sequenceNumber, pktInfo.fromID, pktInfo.toID, pktInfo.msgID);
                parseState = ParseState::PACKET_ERROR;
            }
            break;
        }
        case ParseState::PACKET_HANDLING:
        {
            if (callback)
                callback(*this);
            else
                Debug.printf("No callback set for packet handling\n");
            parseState = ParseState::AWAIT_START;
            break;
        }
        case ParseState::PACKET_ERROR:
        {
            Debug.println("Packet error, resetting parser state");
            parseState = ParseState::AWAIT_START;
            break;
        }
        default:
            parseState = ParseState::AWAIT_START;
            break;
        }
    }
};
#endif // PACKET_PARSER_H