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
    const uint8_t UPLOAD = 0x07; // equivalent to msgID::UPLOAD
    const uint8_t ACK = 0x08;
    const uint8_t NAK = 0x09;
    const uint8_t RESET = 0x0A;
    const uint8_t QUIT = 0x0B;
    const uint8_t CONNECT = 0x0C;
    const uint8_t DISCONNECT = 0x0D;
    const uint8_t MOVE = 0x0E;
}


struct __attribute__((packed)) Pose
{   uint8_t msg_id = msgID::MOVE;
    float angle[6];
};

template <typename StreamType>
void sendPacket(StreamType &serial, uint32_t seq, const uint8_t *payload, uint32_t payloadLen, uint8_t toID)
{   
    static FastCRC32 mcrc32;
    static uint32_t index, crc, packetLen;
    static DMAMEM uint8_t sendBuffer[SEND_BUFFER_SIZE];
    index = 0;
    crc = 0;
    packetLen = payloadLen + PACKET_OVERHEAD;
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
    // Debug.printf("msgID : %02X|", payload[0]);
    // for (uint32_t i = 0; i < index; i++)
    // Debug.printf("%02X ", sendBuffer[i]);
    // Debug.println();
    serial.write(sendBuffer, index);
}

template <typename StreamType>
void heartbeat(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::HEARTBEAT, 1, toID);
}

template <typename StreamType>
void enable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::ENABLE, 1, toID);
}

template <typename StreamType>
void play(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::PLAY, 1, toID);
}

template <typename StreamType>
void pause(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::PAUSE, 1, toID);
}

template <typename StreamType>
void stop(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::STOP, 1, toID);
}

template <typename StreamType>
void disable(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::DISABLE, 1, toID);
}

template <typename StreamType> // more work needed here to send back shape
void upload(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::UPLOAD, 1, toID);
}

template <typename StreamType>
void quit(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::QUIT, 1, toID);
}

template <typename StreamType>
void connect(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::CONNECT, 1, toID);
}

template <typename StreamType>
void disconnect(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::DISCONNECT, 1, toID);
}

template <typename StreamType>
void reset(StreamType &serial, uint32_t seq, uint8_t toID)
{
    sendPacket(serial, seq, &msgID::RESET, 1, toID);
}

template <typename StreamType>
void move(StreamType &serial, uint32_t seq, uint8_t toID, const Pose &pose)
{
    const uint8_t* bytes = reinterpret_cast<const uint8_t*>(&pose);
    sendPacket(serial, seq, bytes, sizeof(Pose), toID);
}


template <typename StreamType>
void ack(StreamType &serial, uint32_t seq, uint8_t msgID, uint8_t toID)
{
    uint8_t payload[2] = {msgID::ACK, msgID};
    sendPacket(serial, seq, payload, 2, toID);
}

template <typename StreamType>
void nak(StreamType &serial, uint32_t seq, uint8_t msgID, uint8_t toID)
{
    uint8_t payload[2] = {msgID::NAK, msgID};
    sendPacket(serial, seq, payload, 2, toID);
}
#endif // MESSAGES_H