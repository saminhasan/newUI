#include "imports.h"
#include <messages.h>
void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  while (!Serial.dtr())
    ;
  delay(1000); // Wait for DTR to stabilize
  Debug.printf("%lu\n", maxArrayLength);
  if (CrashReport)
  {
    Debug.printf("Crash report:\n");
  }
}
void serialEvent()
{
  parser.packetBuffer.readStream(Serial);
}


void loop()
{
  serialEvent();
  digitalWrite(LED_BUILTIN, Serial.dtr());
  parser.parse();
}

// Now define the callback function
void handlePacket(Parser<MAX_PACKET_SIZE> &parser)
{
    const PacketInfo &pktInfo = parser.pktInfo;
    switch (pktInfo.msgID)
    {
        case msgID::HEARTBEAT:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::HEARTBEAT);
            break;
        case msgID::ENABLE:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::ENABLE);
            break;
        case msgID::PLAY:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::PLAY);
            break;
        case msgID::PAUSE:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::PAUSE);
            break;
        case msgID::STOP:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::STOP);
            break;
        case msgID::DISABLE:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::DISABLE);
            break;
        case msgID::UPLOAD:
            arrayLength = pktInfo.payloadSize / (6 * sizeof(float));
            if (arrayLength > maxArrayLength)
            {
                Debug.printf("Error: arrayLength %u > max %u\n", arrayLength, maxArrayLength);
                nak(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::UPLOAD);
            }
            else
            {
                parser.packetBuffer.readBytes(dataBuffer.bytes, pktInfo.payloadSize);
                Debug.printf("%lu : DATA: %u rows\n", pktInfo.sequenceNumber, arrayLength);
                ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::UPLOAD);
                move(Serial, 1000, NODE_ID_PC, dataBuffer.data[0]);
                // printArray(dataBuffer.data, arrayLength);
            }
            break;
        case msgID::RESET:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::RESET);
            break;
        case msgID::QUIT:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::QUIT);
            break;
        case msgID::CONNECT:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::CONNECT);
            break;
        case msgID::DISCONNECT:
            ack(Serial, pktInfo.sequenceNumber, NODE_ID_PC, msgID::DISCONNECT);
            break;
        default:
            Debug.printf("Unknown msgID: 0x%02X\n", pktInfo.msgID);
            break;
    }
}
