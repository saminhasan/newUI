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
            // Debug.printf("%lu : HEARTBEAT received\n", pktInfo.sequenceNumber);
            ack(Serial, pktInfo.sequenceNumber, msgID::HEARTBEAT, 255);
            break;
        case msgID::ENABLE:
            Debug.printf("%lu : ENABLE received\n", pktInfo.sequenceNumber);
            enable(Serial, pktInfo.sequenceNumber, 255);
            ack(Serial, pktInfo.sequenceNumber, msgID::ENABLE, 255);

            break;
        case msgID::PLAY:
            play(Serial, pktInfo.sequenceNumber, 255);
            ack(Serial, pktInfo.sequenceNumber, msgID::PLAY, 255);

            break;
        case msgID::PAUSE:
            pause(Serial, pktInfo.sequenceNumber, 255);
            ack(Serial, pktInfo.sequenceNumber, msgID::PAUSE, 255);
            break;
        case msgID::STOP:
            stop(Serial, pktInfo.sequenceNumber, 255);
            ack(Serial, pktInfo.sequenceNumber, msgID::STOP, 255);
            break;
        case msgID::DISABLE:
            disable(Serial, pktInfo.sequenceNumber, 255);
            ack(Serial, pktInfo.sequenceNumber, msgID::DISABLE, 255);
            break;
        case msgID::DATA:
            arrayLength = pktInfo.payloadSize / (6 * sizeof(float));
            if (arrayLength > maxArrayLength)
            {
                Debug.printf("Error: arrayLength %u > max %u\n", arrayLength, maxArrayLength);
                nak(Serial, pktInfo.sequenceNumber, msgID::DATA, 255);
            }
            else
            {
                parser.packetBuffer.readBytes(dataBuffer.bytes, pktInfo.payloadSize);
                Debug.printf("%lu : DATA: %u rows\n", pktInfo.sequenceNumber, arrayLength);
                ack(Serial, pktInfo.sequenceNumber, msgID::DATA, 255);
                // printArray(dataBuffer.data, arrayLength);
            }
            break;
        default:
            Debug.printf("Unknown msgID: 0x%02X\n", pktInfo.msgID);
            break;
    }
}
