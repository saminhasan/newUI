#ifndef GLOBALS_H
#define GLOBALS_H
#include "constants.h"
#include <FastCRC.h>
#include <Arduino.h>
#include <FlexCAN_T4.h>

uint8_t sendBuffer[SEND_BUFFER_SIZE];
DMAMEM uint8_t recvBuffer[RECV_BUFFER_SIZE];


uint8_t MsgID = 0;
uint8_t response = 0;
uint8_t request = 0;
FlexCAN_T4<CAN1, RX_SIZE_8, TX_SIZE_8> Can1;
FlexCAN_T4<CAN2, RX_SIZE_8, TX_SIZE_8> Can2;
float MoveData[6];
// volatile float targetPos = 0.0f;
bool doPlay = false; // gain scheduling
#endif // GLOBALS_H