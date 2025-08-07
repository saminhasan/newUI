#ifndef MSG_ID_H
#define MSG_ID_H

#include <stdint.h>
#define START_MARKER 0x01
#define END_MARKER   0x04
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