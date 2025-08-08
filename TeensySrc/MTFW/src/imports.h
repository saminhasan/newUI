#ifndef IMPORTS_H
#define IMPORTS_H
#include <globals.h>
#include <messages.h>
#include <PacketParser.h>

uint32_t arrayLength = 0;

void handlePacket(Parser<MAX_PACKET_SIZE> &parser);

Parser<MAX_PACKET_SIZE> parser(ringBufferArray, handlePacket);

#endif // IMPORTS_H