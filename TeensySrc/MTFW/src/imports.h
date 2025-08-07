#ifndef IMPORTS_H
#define IMPORTS_H
#include <globals.h>
#include <MsgID.h>
#include <PacketParser.h>

uint32_t arrayLength = 0;

void handlePacket(Parser<PACKET_BUFFER_SIZE> &parser);

Parser<PACKET_BUFFER_SIZE> parser(ringBufferArray, handlePacket);

#endif // IMPORTS_H