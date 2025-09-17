#ifndef GLOBALS_H
#define GLOBALS_H
#include "constants.h"
#include "LPF.h"
#include <FastCRC.h>
#include <Arduino.h>
#include <USBHost_t36.h>

EXTMEM DataBuffer dataBuffer;
uint8_t sendBuffer[SEND_BUFFER_SIZE];
DMAMEM uint8_t recvBuffer[RECV_BUFFER_SIZE];
DMAMEM uint8_t recvBufferA[RECV_BUFFER_SIZE];
DMAMEM uint8_t recvBufferB[RECV_BUFFER_SIZE];
DMAMEM uint8_t recvBufferC[RECV_BUFFER_SIZE];

//
//
USBHost myusb;
USBHub hub1(myusb);
USBHub hub2(myusb);
USBHub hub3(myusb);

USBSerial_BigBuffer teensyX(myusb, 1);
USBSerial_BigBuffer teensyY(myusb, 2);
USBSerial_BigBuffer teensyZ(myusb, 3);
//
//

size_t readIndex = 0;
size_t arrayLength = 0;
uint8_t MsgID = 0;
uint8_t response = 0;
uint8_t request = 0;

float MoveData[6];

bool doPlay = false;
bool hasData = false;


const uint32_t frMax = 100;
volatile uint32_t feedRate = 0;
volatile uint32_t frRemainder = 0;

volatile bool irqSend = false;

inline const float* getRow(uint32_t i) 
{
    if (arrayLength == 0) return nullptr;
    return dataBuffer.data[i % arrayLength];
}

LPF<100> slider(0.1, 1e-3);

#endif // GLOBALS_H