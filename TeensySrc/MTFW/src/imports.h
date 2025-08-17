#ifndef IMPORTS_H
#define IMPORTS_H
#include <globals.h>
#include <messages.h>
#include <PacketParser.h>

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
    logInfo(Serial,"Rebooting in...");
    for (int i = 5; i > 0; i--)
    {
        logInfo(Serial,"%d... \n", i);
        wait(64);
    }
    logInfo(Serial,"\nReboot");
    ack(Serial, sequenceNumber, NODE_ID_PC, msgID::RESET);
    wait(100);
    USB1_USBCMD = 0;
    SCB_AIRCR = 0x05FA0004;
}
#endif // IMPORTS_H