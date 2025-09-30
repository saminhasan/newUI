#ifndef CONSTANTS_H
#define CONSTANTS_H

#include <stddef.h>
#include <stdint.h>

// #define debug SerialUSB1
static constexpr uint8_t NODE_ID_MASTER = 0x00;
static constexpr uint8_t NODE_ID_PC = 0xFF;
static constexpr uint8_t NODE_ID = 0x0C;


static constexpr uint8_t AXIS_L = 2 * (NODE_ID - 0x0A) + 1;
static constexpr uint8_t AXIS_R = 2 * (NODE_ID - 0x0A) + 2;

static constexpr uint8_t START_MARKER = 0x01;
static constexpr size_t START_SIZE = 1;
static constexpr size_t START_OFFSET = 0;
static constexpr size_t LEN_SIZE = 4;
static constexpr size_t LEN_OFFSET = START_OFFSET;
static constexpr size_t SEQ_SIZE = 4;
static constexpr size_t SEQ_OFFSET = LEN_OFFSET + LEN_SIZE;
static constexpr size_t FROM_SIZE = 1;
static constexpr size_t FROM_OFFSET = SEQ_OFFSET + SEQ_SIZE;
static constexpr size_t TO_SIZE = 1;
static constexpr size_t TO_OFFSET = FROM_OFFSET + FROM_SIZE;
static constexpr size_t MSG_ID_SIZE = 1;
static constexpr size_t MSG_ID_OFFSET = TO_OFFSET + TO_SIZE;
static constexpr size_t CRC_SIZE = 4;
static constexpr size_t PACKET_OVERHEAD = START_SIZE + LEN_SIZE + SEQ_SIZE + FROM_SIZE + TO_SIZE + MSG_ID_SIZE + CRC_SIZE;
static constexpr size_t MIN_PACKET_SIZE = PACKET_OVERHEAD;
static constexpr size_t HEADER_SIZE = PACKET_OVERHEAD - START_SIZE - CRC_SIZE; // LEN + SEQ + FROM + TO + MSG_ID
static constexpr size_t MAX_PACKET_SIZE = size_t(16 * 1024 * 1024 + PACKET_OVERHEAD);

static constexpr size_t SEND_BUFFER_SIZE     = size_t(65536); // 64 KB = at 60 MB/s / 1ms
static constexpr size_t RECV_BUFFER_SIZE     = size_t(65536); // 64 KB = at 60 MB/s / 1ms
static constexpr size_t TEMP_BUFFER_SIZE     = size_t(1024); // 1 KB
static constexpr size_t PSRAM_SIZE           = size_t(16 * 1024 * 1024);
static constexpr size_t NUM_COL              = size_t(6);
static constexpr size_t ROW_SIZE             = NUM_COL * sizeof(float);
static constexpr size_t maxArrayLength       = size_t(PSRAM_SIZE / ROW_SIZE);


namespace msgID
{
    static constexpr uint8_t HEARTBEAT   = 0x01;
    static constexpr uint8_t ENABLE      = 0x02;
    static constexpr uint8_t PLAY        = 0x03;
    static constexpr uint8_t PAUSE       = 0x04;
    static constexpr uint8_t STOP        = 0x05;
    static constexpr uint8_t DISABLE     = 0x06;
    static constexpr uint8_t UPLOAD      = 0x07;
    static constexpr uint8_t ACK         = 0x08;
    static constexpr uint8_t NAK         = 0x09;
    static constexpr uint8_t RESET       = 0x0A;
    static constexpr uint8_t QUIT        = 0x0B;
    static constexpr uint8_t CONNECT     = 0x0C;
    static constexpr uint8_t DISCONNECT  = 0x0D;
    static constexpr uint8_t MOVE        = 0x0E;
    static constexpr uint8_t FEEDBACK    = 0x0F;
    static constexpr uint8_t INFO        = 0xFD;
    static constexpr uint8_t UNKNOWN     = 0xFE;
    static constexpr uint8_t MAX_VALUE   = UNKNOWN;
}
constexpr size_t MAX_MSG_ID = msgID::MAX_VALUE;
static inline const char* msgID_toStr(uint8_t id)
{
    switch (id)
    {
        case msgID::HEARTBEAT:   return "HEARTBEAT";
        case msgID::ENABLE:      return "ENABLE";
        case msgID::PLAY:        return "PLAY";
        case msgID::PAUSE:       return "PAUSE";
        case msgID::STOP:        return "STOP";
        case msgID::DISABLE:     return "DISABLE";
        case msgID::UPLOAD:      return "UPLOAD";
        case msgID::ACK:         return "ACK";
        case msgID::NAK:         return "NAK";
        case msgID::RESET:       return "RESET";
        case msgID::QUIT:        return "QUIT";
        case msgID::CONNECT:     return "CONNECT";
        case msgID::DISCONNECT:  return "DISCONNECT";
        case msgID::MOVE:        return "MOVE";
        case msgID::FEEDBACK:    return "FEEDBACK";
        case msgID::INFO:        return "INFO";
        case msgID::UNKNOWN:     return "UNKNOWN";
        default:                 return "INVALID";
    }
}


static inline float rad2deg(float radians) {
    return radians * 57.29577951308232f;  // 180 / pi
}

static inline float deg2rad(float degrees) {
    return degrees * 0.0174532925199433f; // pi / 180
}

#endif // CONSTANTS_H
