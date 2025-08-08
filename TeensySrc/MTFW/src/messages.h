#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>
#include <globals.h>
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
    const uint8_t DATA = 0x07;
    const uint8_t ACK = 0x08;
    const uint8_t NAK = 0x09;
    const uint8_t RESET = 0x0A;
}

FastCRC32 mcrc32;

uint32_t createPacket(uint32_t seq, const uint8_t *payload, uint32_t payloadLen, uint8_t toID)
{
    uint32_t index = 0;
    uint32_t crc = 0;
    uint32_t packetLen = payloadLen + PACKET_OVERHEAD;
    sendBuffer[index] = START_MARKER; index++;
    memcpy(&sendBuffer[index], &packetLen, sizeof(packetLen)); index += sizeof(packetLen);
    memcpy(&sendBuffer[index], &seq, sizeof(seq)); index += sizeof(seq);
    sendBuffer[index] = NODE_ID; index++;
    sendBuffer[index] = toID; index++;
    mcrc32.crc32(&sendBuffer[1], 10);
    crc = mcrc32.crc32_upd(payload, payloadLen);
    memcpy(&sendBuffer[index], &crc, sizeof(crc));
    index += sizeof(crc);
    memcpy(&sendBuffer[index], payload, payloadLen);
    index += payloadLen;
    sendBuffer[index++] = END_MARKER;
    Debug.printf("msgID : %02X|", payload[0]);
    for (uint32_t i = 0; i < index; i++)
    Debug.printf("%02X ", sendBuffer[i]);
    Debug.println();
    return index;
}
template <typename StreamType>
void heartbeat(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::HEARTBEAT;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void enable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::ENABLE;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void play(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::PLAY;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void pause(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::PAUSE;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void stop(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::STOP;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void disable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::DISABLE;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void reset(StreamType &serial, uint32_t seq, uint8_t toID)
{
    uint8_t payload = msgID::RESET;
    uint32_t packetSize = createPacket(seq, &payload, 1, toID);
    serial.write(sendBuffer, packetSize);
}
template <typename StreamType>
void ack(StreamType &serial, uint32_t seq, uint8_t msgID, uint8_t toID)
{
    uint8_t payload[2] = {msgID::ACK, msgID};
    uint32_t packetSize = createPacket(seq, payload, 2, toID);
    serial.write(sendBuffer, packetSize);
}

template <typename StreamType>
void nak(StreamType &serial, uint32_t seq, uint8_t msgID, uint8_t toID)
{
    uint8_t payload[2] = {msgID::NAK, msgID};
    uint32_t packetSize = createPacket(seq, payload, 2, toID);
    serial.write(sendBuffer, packetSize);
}
#endif // MESSAGES_H