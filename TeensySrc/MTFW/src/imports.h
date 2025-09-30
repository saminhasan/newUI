#ifndef IMPORTS_H
#define IMPORTS_H
#include "constants.h"
#include "globals.h"
#include "RingBuffer.h"
#include "PacketParser.h"
#include "delf.h"


IntervalTimer motorTimer;
RingBuffer ringBuffer(recvBuffer, sizeof(recvBuffer));
RingBuffer ringBufferA(recvBufferA, sizeof(recvBufferA));
RingBuffer ringBufferB(recvBufferB, sizeof(recvBufferB));
RingBuffer ringBufferC(recvBufferC, sizeof(recvBufferC));
PacketParser packetParser(ringBuffer);
PacketParser packetParserA(ringBufferA);
PacketParser packetParserB(ringBufferB);
PacketParser packetParserC(ringBufferC);

void onPacketReceived(const PacketInfo &packet);

void initUSBHost()
{
}

void motorTick()
{  
  digitalWrite(SCOPE_PIN, HIGH);

  
  if(!doPlay) return;

  float LPFy = slider.update(feedRate);
  frRemainder += ((uint32_t)(LPFy));
  uint32_t deltaIndex = floor(frRemainder / frMax);
  frRemainder %= frMax;
  readIndex = (readIndex + deltaIndex) % arrayLength;
  //  logInfo(Serial," U : %lu, Y: %f", feedRate, LPFy);
  const float *row = getRow(readIndex);
  if (row)
  {
    memcpy(MoveData, row, sizeof(MoveData));
  }
  move(teensyX, 0, 0x0A, MoveData);
  move(teensyY, 0, 0x0B, MoveData);
  move(teensyZ, 0, 0x0C, MoveData);
  irqSend = true;
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
  logInfo(Serial, "Rebooting in...\n");
  // debug.printf("Rebooting in...\n");
  for (int i = 5; i > 0; i--)
  {
    logInfo(Serial, "%d... \n", i);
    wait(64);
  }
  logInfo(Serial, "Rebooting in 1 Second\n");
  // debug.printf("Rebooting in 1 Second\n");

  ack(Serial, sequenceNumber, NODE_ID_PC, msgID::RESET);
  wait(1000);
  USB1_USBCMD = 0;
  SCB_AIRCR = 0x05FA0004;
}
#endif // IMPORTS_H