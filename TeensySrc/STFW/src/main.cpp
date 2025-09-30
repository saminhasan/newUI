#include "imports.h"
#include <util/atomic.h>
extern uint32_t external_psram_size;

void setup()
{
    pinMode(LED_BUILTIN, OUTPUT);
    while (!Serial.dtr())
        ;
    delay(1000);
    initCAN();
    motorL.init();
    motorR.init();
    if (CrashReport)
        logInfo(Serial, "Crash report:%s\n", String(CrashReport).c_str());
    logInfo(Serial, "External PSRAM size: %lu MB\n", external_psram_size );
    packetParser.setCallback(onPacketReceived);
    motorTimer.begin(motorTick, 1000); // 1 kHz
    // motorTimer.priority(255);           // lowest priority
    logInfo(Serial, "Motor L: axisId=%d | dir=%d\n", motorL.axisId, motorL.dir);
    logInfo(Serial, "Motor R: axisId=%d | dir=%d\n", motorR.axisId, motorR.dir);
    logInfo(Serial, "Setup complete. Node ID: 0x%02X | AXIS_L: %d | AXIS_R: %d\n", NODE_ID, AXIS_L, AXIS_R);
}
void serialEvent()
{
    ringBuffer.readStream(Serial);
}

void loop()
{
    packetParser.parse();
    motorL.tick();motorR.tick();
}

void onPacketReceived(const PacketInfo &packet)
{
    switch (packet.msgID)
    {
    case msgID::HEARTBEAT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::HEARTBEAT);
        break;
    case msgID::ENABLE:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::ENABLE);
        motorL.resetGain(); motorR.resetGain();
        motorL.enable();motorR.enable();
        motorL.calibrate();motorR.calibrate();
        break;
    case msgID::PLAY:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::PLAY);
        doPlay = true;
        motorL.setGain(); motorR.setGain();
        break;
    case msgID::PAUSE:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::PAUSE);
        doPlay = false;        motorL.resetGain(); motorR.resetGain();
        break;
    case msgID::STOP:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::STOP);
        doPlay = false;        motorL.resetGain(); motorR.resetGain();

        break;

    case msgID::DISABLE:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::DISABLE);
                motorL.resetGain(); motorR.resetGain();

        motorL.disable(); motorR.disable();
        doPlay = false;
        break;
    case msgID::RESET:
        doPlay = false; // should disarm motors
        motorL.resetGain(); motorR.resetGain();
        motorL.disable(); motorR.disable();
        Reboot(packet.sequence);
        break;
    case msgID::QUIT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::QUIT);
        motorL.resetGain(); motorR.resetGain();
        motorL.disable(); motorR.disable();
        doPlay = false;
        break;
    case msgID::CONNECT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::CONNECT);
        break;
    case msgID::DISCONNECT:
        ack(Serial, packet.sequence, NODE_ID_PC, msgID::DISCONNECT);
        motorL.resetGain(); motorR.resetGain();
        motorL.disable(); motorR.disable();
        break;
    case msgID::MOVE:
        // ack(Serial, packet.sequence, NODE_ID_PC, msgID::MOVE);
        // logInfo(Serial, "MOVE : [%f, %f, %f, %f, %f, %f]\n",MoveData[0], MoveData[1], MoveData[2],MoveData[3], MoveData[4], MoveData[5]);
        // ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        // {
            // targetPos = deg2rad(MoveData[0]);
        // }
        // if (!doPlay)
            // targetPos = deg2rad(MoveData[0]);
        motorL.setPositionSetpoint(MoveData[AXIS_L-1]);
        motorR.setPositionSetpoint(MoveData[AXIS_R-1]);
        break;
    default:
        // debug.printf("Unknown msgID: 0x%02X\n", packet.msgID);
        break;
    }
}

void ext_output1(const CAN_message_t& msg) {
    switch (msg.bus)
    {
    case 0x01:
        motorL.canRecv(msg);
        break;
    case 0x02:
        motorR.canRecv(msg);
        break;
    default:
        break;
    }
}