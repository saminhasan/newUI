#include "imports.h"
#include <util/atomic.h>
extern uint32_t external_psram_size;

void setup()
{
    pinMode(SCOPE_PIN, OUTPUT);
    digitalWrite(SCOPE_PIN, LOW);
    pinMode(LED_BUILTIN, OUTPUT);
    while (!Serial.dtr())
        ;
    myusb.begin();
    while (!(teensyX && teensyY && teensyZ))
    {
        myusb.Task();
        yield();
    }
    delay(1000);
    initUSBHost();

    // debug.printf("%lu\n", maxArrayLength);
    if (CrashReport)
        logInfo(Serial, "Crash report:%s\n", String(CrashReport).c_str());
    logInfo(Serial, "External PSRAM size: %lu MB\n", external_psram_size);
    packetParser.setCallback(onPacketReceived);
    packetParserA.setCallback(onPacketReceived);
    packetParserB.setCallback(onPacketReceived);
    packetParserC.setCallback(onPacketReceived);
    motorTimer.begin(motorTick, 1000); // 1 kHz
    motorTimer.priority(255);          // lowest priority
}
void serialEvent()
{
    ringBuffer.readStream(Serial);
}
void hostEvent()
{
    myusb.Task();
    ringBufferA.readStream(teensyX);

    myusb.Task();
    ringBufferB.readStream(teensyY);
    
    myusb.Task();
    ringBufferC.readStream(teensyZ);

    if (ringBufferA.size() > 0 || ringBufferB.size() > 0 || ringBufferC.size() > 0)
    // logInfo(Serial, "X:%d Y:%d Z:%d\n", ringBufferA.size(), ringBufferB.size(), ringBufferC.size());
    myusb.Task();
}
void loop()
{
    myusb.Task();
    packetParser.parse();
    packetParserA.parse();
    packetParserB.parse();
    packetParserC.parse();
    if (doPlay && hasData)
    {
        if (irqSend)
        {
            irqSend = false;
            teensyX.flush();teensyY.flush();teensyZ.flush();
            myusb.Task();
            digitalWrite(SCOPE_PIN, LOW);
        }
    }
    hostEvent();
    /*
struct __attribute__((packed)) Feedback
{
    uint8_t axisId;                   // 1
    uint8_t mode;                     // 1
    uint8_t armed;                    // 1
    uint8_t calibrated;               // 1
    float setPoint;                   // 4
    uint32_t tSend;                   // 4
    uint32_t tRecv;                   // 4
    uint8_t sent[MOTCTRL_FRAME_SIZE]; // 8
    uint8_t recv[MOTCTRL_FRAME_SIZE]; // 8
};
 */
    // if (feedbackCounter == 6)
    // {
    //     feedbackCounter = 0;
    //     for (int i = 0; i < 6; i++)
    //         logInfo(Serial, "FB[%d] setPoint=%.3f", i, feedbacks[i].setPoint);
    // }
}

void onPacketReceived(const PacketInfo &packet)
{
    const float *row = nullptr;
    switch (packet.msgID)
    {
    case msgID::HEARTBEAT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::HEARTBEAT);
        break;
    case msgID::ENABLE:
        // ack(Serial, packet.sequence, NODE_ID_PC, msgID::ENABLE);
        enable(teensyX, 0, 0x0A);
        enable(teensyY, 0, 0x0B);
        enable(teensyZ, 0, 0x0C);
        break;
    case msgID::PLAY:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::PLAY);
        doPlay = true;
        play(teensyX, 0, 0x0A);
        play(teensyY, 0, 0x0B);
        play(teensyZ, 0, 0x0C);
        feedRate = 100;
        break;
    case msgID::PAUSE:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::PAUSE);
        // pause(teensyX, 0, 0x0A);
        // pause(teensyY, 0, 0x0B);
        // pause(teensyZ, 0, 0x0C);
        feedRate = 0;
        break;
    case msgID::STOP:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::STOP);
        doPlay = false;
        stop(teensyX, 0, 0x0A);
        stop(teensyY, 0, 0x0B);
        stop(teensyZ, 0, 0x0C);
        feedRate = 0;

        break;

    case msgID::DISABLE:
        // ack(Serial, packet.sequence, NODE_ID_PC, msgID::DISABLE);
        disable(teensyX, 0, 0x0A);
        disable(teensyY, 0, 0x0B);
        disable(teensyZ, 0, 0x0C);
        feedRate = 0;
        doPlay = false;
        break;
    case msgID::UPLOAD:
        // debug.printf("%lu : DATA: %u rows\n", packet.sequence, arrayLength);
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::UPLOAD);

        row = getRow(0);
        memcpy(MoveData, row, sizeof(MoveData));
        move(teensyX, 0, 0x0A, MoveData);
        move(teensyY, 0, 0x0B, MoveData);
        move(teensyZ, 0, 0x0C, MoveData);
        hasData = true;
        break;
    case msgID::RESET:
        Reboot(packet.sequence);
        hasData = false;
        doPlay = false;
        reset(teensyX, 0, 0x0A);
        reset(teensyY, 0, 0x0B);
        reset(teensyZ, 0, 0x0C);
        feedRate = 0;

        break;
    case msgID::QUIT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::QUIT);
        hasData = false;
        doPlay = false;
        stop(teensyX, 0, 0x0A);
        stop(teensyY, 0, 0x0B);
        stop(teensyZ, 0, 0x0C);
        feedRate = 0;

        break;
    case msgID::CONNECT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::CONNECT);
        connect(teensyX, 0, 0x0A);
        connect(teensyY, 0, 0x0B);
        connect(teensyZ, 0, 0x0C);

        break;
    case msgID::DISCONNECT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::DISCONNECT);
        disconnect(teensyX, 0, 0x0A);
        disconnect(teensyY, 0, 0x0B);
        disconnect(teensyZ, 0, 0x0C);
        break;
    case msgID::MOVE:
        if(!doPlay)
            {
                ack(Serial, packet.sequence, NODE_ID_PC, msgID::MOVE);
                move(teensyX, 0, 0x0A, MoveData);
                move(teensyY, 0, 0x0B, MoveData);
                move(teensyZ, 0, 0x0C, MoveData);
            }
        break;
    case msgID::FEEDBACK:
        sendFeedback(Serial, feedback);
        break;

    default:
        // debug.printf("Unknown msgID: 0x%02X\n", packet.msgID);
        break;
    }
}
