#ifndef IMPORTS_H
#define IMPORTS_H
#include "constants.h"
#include "globals.h"
#include "RingBuffer.h"
#include "PacketParser.h"
#include "messages.h"
#include "delf.h"
IntervalTimer motorTimer;
RingBuffer ringBuffer(recvBuffer, sizeof(recvBuffer));
PacketParser packetParser(ringBuffer);
void onPacketReceived(const PacketInfo& packet);

Axis motorL = Axis(AXIS_L);
Axis motorR = Axis(AXIS_R);



void initCAN()
{
    Can1.begin();
    Can1.setBaudRate(500000);
    Can1.setMaxMB(16);
    Can1.enableFIFO();
    Can1.enableFIFOInterrupt();
    Can1.mailboxStatus();

    Can2.begin();
    Can2.setBaudRate(500000);
    Can2.setMaxMB(16);
    Can2.enableFIFO();
    Can2.enableFIFOInterrupt();
    Can2.mailboxStatus();


    return;
}

void motorTick()
{ 
    motorL.update();
    motorR.update();
}

void wait(unsigned long ms)
{
  static unsigned long start = 0;
  start = millis();
  while (millis() - start < ms)
  {
    // tick();
    yield();
  }
}
void Reboot(uint32_t sequenceNumber)
{
    logInfo(Serial,"Rebooting in...\n");
    // debug.printf("Rebooting in...\n");
    for (int i = 5; i > 0; i--)
    {
        logInfo(Serial,"%d... \n", i);
        wait(64);
    }
    logInfo(Serial,"Rebooting in 1 Second\n");
    // debug.printf("Rebooting in 1 Second\n");

    ack(Serial, sequenceNumber, NODE_ID_PC, msgID::RESET);
    wait(1000);
    USB1_USBCMD = 0;
    SCB_AIRCR = 0x05FA0004;
}
#endif // IMPORTS_H