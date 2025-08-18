#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>
#include "globals.h"
#include <FastCRC.h>

#define START_MARKER 0x01
#define END_MARKER 0x04

namespace msgID
{
    const uint8_t HEARTBEAT = 0x01;
    const uint8_t ENABLE = 0x02;
    const uint8_t PLAY = 0x03;
    const uint8_t PAUSE = 0x04;
    const uint8_t STOP = 0x05;
    const uint8_t DISABLE = 0x06;
    const uint8_t UPLOAD = 0x07; // equivalent to msgID::UPLOAD
    const uint8_t ACK = 0x08;
    const uint8_t NAK = 0x09;
    const uint8_t RESET = 0x0A;
    const uint8_t QUIT = 0x0B;
    const uint8_t CONNECT = 0x0C;
    const uint8_t DISCONNECT = 0x0D;
    const uint8_t MOVE = 0x0E;
    const uint8_t INFO = 0xFE;
    const uint8_t UNKNOWN = 0xFF; // For unknown message IDs
}
FastCRC32 mcrc32;

template <typename StreamType>
void sendPacket(StreamType& serial, uint32_t payloadLen, uint32_t seq, uint8_t toID, uint8_t msgID, const uint8_t* payload)
{
    static uint32_t index, crc, packetLen;
    index = 0;
    crc = 0;
    packetLen = payloadLen + PACKET_OVERHEAD + 1;
    sendBuffer[index] = START_MARKER; index++;
    memcpy(&sendBuffer[index], &packetLen, sizeof(packetLen)); index += sizeof(packetLen);
    memcpy(&sendBuffer[index], &seq,       sizeof(seq));       index += sizeof(seq);
    sendBuffer[index] = NODE_ID; index++;
    sendBuffer[index] = toID; index++;
    mcrc32.crc32(&sendBuffer[1], index - 1);
    if (payloadLen)
    {
        mcrc32.crc32_upd(&msgID, 1);
        crc = mcrc32.crc32_upd(payload, payloadLen);
    }
    else
        crc = mcrc32.crc32_upd(&msgID, 1);
    memcpy(&sendBuffer[index], &crc, sizeof(crc)); index += sizeof(crc);
    sendBuffer[index] = msgID; index++;
    if (payloadLen) {
        memcpy(&sendBuffer[index], payload, payloadLen);
        index += payloadLen;
    }
    sendBuffer[index] = END_MARKER; index++;
    serial.write(sendBuffer, index);
}

template <typename StreamType>
void heartbeat(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::HEARTBEAT, nullptr);
}

template <typename StreamType>
void enable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::ENABLE, nullptr);
}

template <typename StreamType>
void play(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::PLAY, nullptr);
}

template <typename StreamType>
void pause(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::PAUSE, nullptr);
}

template <typename StreamType>
void stop(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::STOP, nullptr);
}

template <typename StreamType>
void disable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::DISABLE, nullptr);
}

template <typename StreamType> // more work needed here to send back shape
void upload(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::UPLOAD, nullptr);
}

template <typename StreamType>
void quit(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::QUIT, nullptr);
}

template <typename StreamType>
void connect(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::CONNECT, nullptr);
}

template <typename StreamType>
void disconnect(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::DISCONNECT, nullptr);
}

template <typename StreamType>
void reset(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, 0, seq, toID, msgID::RESET, nullptr);
}

template <typename StreamType>
void move(StreamType &serial, uint32_t seq, uint8_t toID, const float array[6])
{
    sendPacket(serial, sizeof(float) * 6, seq, toID, msgID::MOVE, reinterpret_cast<const uint8_t*>(array));
}


template <typename StreamType>
void ack(StreamType &serial, uint32_t seq, uint8_t toID, uint8_t msgID)
{
    sendPacket(serial, uint32_t(1), seq, toID, msgID::ACK, &msgID);
}

template <typename StreamType>
void nak(StreamType &serial, uint32_t seq, uint8_t toID, uint8_t msgID)
{
    sendPacket(serial, uint32_t(1), seq, toID, msgID::NAK, &msgID);
}

// template <typename StreamType>
// void logInfo(StreamType &serial, const char *fmt, ...)
// {
//     uint32_t seq = millis(); // Use current time as sequence number
//     uint8_t toID = NODE_ID_PC;

//     va_list args;
//     va_start(args, fmt);
//     int len = vsnprintf(nullptr, 0, fmt, args) + 1;
//     va_end(args);

//     char msg[len];
//     va_start(args, fmt);
//     vsnprintf(msg, len, fmt, args);
//     va_end(args);
//     sendPacket(serial, len, seq, toID, msgID::INFO, reinterpret_cast<const uint8_t*>(msg));
// }
template <typename StreamType>
void logInfo(StreamType &serial, const char *fmt, ...)
{
    constexpr size_t BUF_SIZE = 1024;
    static char msg[BUF_SIZE];
    uint32_t seq = millis(); // Use current time as sequence number
    uint8_t toID = NODE_ID_PC;
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(msg, BUF_SIZE, fmt, args) + 1;
    va_end(args);
    if (len > static_cast<int>(BUF_SIZE)) len = BUF_SIZE; // clamp
    sendPacket(serial, len, seq, toID, msgID::INFO, reinterpret_cast<const uint8_t*>(msg));
}
#endif // MESSAGES_H