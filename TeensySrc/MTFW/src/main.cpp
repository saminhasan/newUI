#include "imports.h"
#include <util/atomic.h>
extern uint32_t external_psram_size;

void setup()
{
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
    logInfo(Serial, "External PSRAM size: %lu MB\n", external_psram_size );
    packetParser.setCallback(onPacketReceived);
    packetParserA.setCallback(onPacketReceived);
    packetParserB.setCallback(onPacketReceived);
    packetParserC.setCallback(onPacketReceived);
    motorTimer.begin(motorTick, 1000); // 1 kHz
    motorTimer.priority(255);           // lowest priority
}
void serialEvent()
{
    ringBuffer.readStream(Serial);
    ringBufferA.readStream(teensyX);
    ringBufferB.readStream(teensyY);
    ringBufferC.readStream(teensyZ);
}

void loop()
{   myusb.Task();
    packetParser.parse();
    if(doPlay && hasData)
    {
        if(irqSend)
        {
            irqSend = false;
            move(teensyX, 0, 0x0A, MoveData);
            move(teensyY, 0, 0x0B, MoveData);
            move(teensyZ, 0, 0x0C, MoveData);
        }
    }
}

void onPacketReceived(const PacketInfo &packet)
{
    const float* row = nullptr;
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
        pause(teensyX, 0, 0x0A);
        pause(teensyY, 0, 0x0B);
        pause(teensyZ, 0, 0x0C);
        doPlay = false;
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
        disable(teensyZ, 0, 0x0C);        feedRate = 0;

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
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::MOVE);
        // logInfo(Serial, "MOVE : [%f, %f, %f, %f, %f, %f]\n",MoveData[0], MoveData[1], MoveData[2],MoveData[3], MoveData[4], MoveData[5]);
        // ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        // {
            // targetPos = deg2rad(MoveData[0]);
        // }
        move(teensyX, 0, 0x0A, MoveData);
        move(teensyY, 0, 0x0B, MoveData);
        move(teensyZ, 0, 0x0C, MoveData);
        break;
    case msgID::FEEDBACK:
        logInfo(Serial, "FEEDBACK\n");
    default:
        // debug.printf("Unknown msgID: 0x%02X\n", packet.msgID);
        break;
    }
}
