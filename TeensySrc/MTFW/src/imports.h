#ifndef IMPORTS_H
#define IMPORTS_H
#include "globals.h"
#include "messages.h"
#include "PacketParser.h"

uint32_t arrayLength = 0;
void handlePacket(Parser<MAX_PACKET_SIZE> &parser);
Parser<MAX_PACKET_SIZE> parser(ringBufferArray, handlePacket);
IntervalTimer TickTock;

void ticktok()
{
    logInfo(Serial, "TickTock : %lu", millis());
}

void wait(unsigned long ms)
{
  unsigned long start = millis();
  while (millis() - start < ms)
  {
    // tick();
    yield();
  }
}
void Reboot(uint32_t sequenceNumber)
{
    logInfo(Serial,"Rebooting in...\n");
    Debug.printf("Rebooting in...\n");
    for (int i = 5; i > 0; i--)
    {
        logInfo(Serial,"%d... \n", i);
        wait(64);
    }
    logInfo(Serial,"Rebooting in 1 Second\n");
    Debug.printf("Rebooting in 1 Second\n");

    ack(Serial, sequenceNumber, NODE_ID_PC, msgID::RESET);
    wait(1000);
    USB1_USBCMD = 0;
    SCB_AIRCR = 0x05FA0004;
}
#endif // IMPORTS_H