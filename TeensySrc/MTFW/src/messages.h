#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>
#include "constants.h"
#include "globals.h"


template <typename StreamType>
void sendPacket(StreamType& serial, uint32_t payloadLen, uint32_t seq, uint8_t toID, uint8_t msgID, const uint8_t* payload)
{   
    noInterrupts();
    // make a header struct so that so much memcpy can be avoided
    FastCRC32 crc32;
    uint32_t index, crc, packetLen;
    packetLen = PACKET_OVERHEAD + payloadLen;
    index = 0;
    crc = 0;
    sendBuffer[index] = START_MARKER; index++;
    memcpy(&sendBuffer[index], &packetLen, sizeof(packetLen)); index += sizeof(packetLen);
    memcpy(&sendBuffer[index], &seq,       sizeof(seq));       index += sizeof(seq);
    sendBuffer[index] = NODE_ID; index++;
    sendBuffer[index] = toID; index++;
    sendBuffer[index] = msgID; index++;
    if (payloadLen > 0)
    {
        memcpy(&sendBuffer[index], payload, payloadLen);
        index += payloadLen;
    }
    crc = crc32.crc32(sendBuffer, index);
    memcpy(&sendBuffer[index], &crc, sizeof(crc)); index += sizeof(crc);
    serial.write(sendBuffer, index);
    interrupts();
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
    // debug.printf("logInfo: %s\n", msg);

}
#endif // MESSAGES_H
