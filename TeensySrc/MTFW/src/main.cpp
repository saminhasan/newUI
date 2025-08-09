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
            ack(Serial, pktInfo.sequenceNumber, msgID::HEARTBEAT, NODE_ID_PC);
            break;
        case msgID::ENABLE:
            ack(Serial, pktInfo.sequenceNumber, msgID::ENABLE, NODE_ID_PC);
            break;
        case msgID::PLAY:
            ack(Serial, pktInfo.sequenceNumber, msgID::PLAY, NODE_ID_PC);
            break;
        case msgID::PAUSE:
            ack(Serial, pktInfo.sequenceNumber, msgID::PAUSE, NODE_ID_PC);
            break;
        case msgID::STOP:
            ack(Serial, pktInfo.sequenceNumber, msgID::STOP, NODE_ID_PC);
            break;
        case msgID::DISABLE:
            ack(Serial, pktInfo.sequenceNumber, msgID::DISABLE, NODE_ID_PC);
            break;
        case msgID::UPLOAD:
            arrayLength = pktInfo.payloadSize / (6 * sizeof(float));
            if (arrayLength > maxArrayLength)
            {
                Debug.printf("Error: arrayLength %u > max %u\n", arrayLength, maxArrayLength);
                nak(Serial, pktInfo.sequenceNumber, msgID::UPLOAD, NODE_ID_PC);
            }
            else
            {
                parser.packetBuffer.readBytes(dataBuffer.bytes, pktInfo.payloadSize);
                Debug.printf("%lu : DATA: %u rows\n", pktInfo.sequenceNumber, arrayLength);
                ack(Serial, pktInfo.sequenceNumber, msgID::UPLOAD, NODE_ID_PC);
                Pose pose;
                memcpy(pose.angle, dataBuffer.data[0], sizeof(pose.angle));
                move(Serial, 1000, NODE_ID_PC, pose);
                // printArray(dataBuffer.data, arrayLength);
            }
            break;
        case msgID::RESET:
            ack(Serial, pktInfo.sequenceNumber, msgID::RESET, NODE_ID_PC);
            break;
        case msgID::QUIT:
            ack(Serial, pktInfo.sequenceNumber, msgID::QUIT, NODE_ID_PC);
            break;
        case msgID::CONNECT:
            ack(Serial, pktInfo.sequenceNumber, msgID::CONNECT, NODE_ID_PC);
            break;
        case msgID::DISCONNECT:
            ack(Serial, pktInfo.sequenceNumber, msgID::DISCONNECT, NODE_ID_PC);
            break;
        default:
            Debug.printf("Unknown msgID: 0x%02X\n", pktInfo.msgID);
            break;
    }
}
