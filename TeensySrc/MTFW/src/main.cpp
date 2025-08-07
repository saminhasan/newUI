#include "imports.h"

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
void handlePacket(Parser<PACKET_BUFFER_SIZE> &parser)
{
    const PacketInfo &pktInfo = parser.pktInfo;
    switch (pktInfo.msgID)
    {
        case msgID::HEARTBEAT:
            // Debug.println("HEARTBEAT received");
            break;
        case msgID::ENABLE:
            // Debug.println("ENABLE received");
            break;
        case msgID::PLAY:
            // Debug.println("PLAY received");
            break;
        case msgID::PAUSE:
            // Debug.println("PAUSE received");
            break;
        case msgID::STOP:
            // Debug.println("STOP received");
            break;
        case msgID::DISABLE:
            // Debug.println("DISABLE received");
            break;
        case msgID::DATA:
            arrayLength = pktInfo.payloadSize / (6 * sizeof(float));
            if (arrayLength > maxArrayLength)
            {
                Debug.printf("Error: arrayLength %u > max %u\n", arrayLength, maxArrayLength);
            }
            else
            {
                parser.packetBuffer.readBytes(dataBuffer.bytes, pktInfo.payloadSize);
                // Debug.printf("DATA: %u rows\n", arrayLength);
                // printArray(dataBuffer.data, arrayLength);
            }
            break;
        default:
            Debug.printf("Unknown msgID: 0x%02X\n", pktInfo.msgID);
            break;
    }
}
