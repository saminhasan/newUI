#ifndef MSG_ID_H
#define MSG_ID_H

#include <stdint.h>

// Message ID constants
#define MSG_HEARTBEAT   0x01
#define MSG_ENABLE      0x02
#define MSG_PLAY        0x03
#define MSG_PAUSE       0x04
#define MSG_STOP        0x05
#define MSG_DISABLE     0x06
#define MSG_DATA        0x07
#define START_MARKER 0x01
#define END_MARKER 0x04
// Alternative: using const variables (more type-safe)
namespace msgID {
    const uint8_t HEARTBEAT = 0x01;
    const uint8_t ENABLE    = 0x02;
    const uint8_t PLAY      = 0x03;
    const uint8_t PAUSE     = 0x04;
    const uint8_t STOP      = 0x05;
    const uint8_t DISABLE   = 0x06;
    const uint8_t DATA      = 0x07;
}

#endif // MSG_ID_H