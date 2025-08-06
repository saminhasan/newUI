
#include "imports.h"
#define Debug SerialUSB1
byte b;
void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  while (!Serial.dtr())
    ;
}
void SerialEvent()
{
  packetBuffer.readStream(Serial);
  /*
    size_t available = Serial.available();
    if (available > 0) {
        size_t toRead = (available < USB_SERIAL_BUFFER_SIZE) ? available : USB_SERIAL_BUFFER_SIZE;
        size_t bytesRead = Serial.readBytes(reinterpret_cast<char *>(serialBuffer), toRead);
        packetBuffer.writeBytes(serialBuffer, bytesRead);
    }
  */
}
void loop()
{
  digitalWrite(LED_BUILTIN, Serial.dtr());

  if (packetBuffer.size() >= MIN_PACKET_SIZE)
  {
    uint8_t byte;
    while (packetBuffer.size() > 0 && packetBuffer.pop(byte))
    {
      if (byte == START_MARKER)
      {
        parseState = ParseState::PACKET_FOUND;
        break;
      }
    }
    if (parseState == ParseState::PACKET_FOUND)
    {
      uint8_t headerBuffer[10]; // length(4) + seq(4) + sys(1) + axis(1)
      if (packetBuffer.size() >= 10)
      {
        size_t bytesRead = packetBuffer.readBytes(headerBuffer, 10);

        if (bytesRead == 10)
        {
          pktInfo.packetLength = headerBuffer[0] | (headerBuffer[1] << 8) | (headerBuffer[2] << 16) | (headerBuffer[3] << 24);
          pktInfo.sequenceNumber = headerBuffer[4] | (headerBuffer[5] << 8) | (headerBuffer[6] << 16) | (headerBuffer[7] << 24);
          pktInfo.systemId = headerBuffer[8];
          pktInfo.axisId = headerBuffer[9];
          crc = CRC32.crc32(headerBuffer, 10);
          uint32_t payloadSize = pktInfo.packetLength - 16;
          if (packetBuffer.size() >= (payloadSize + 5))
          {
            if (payloadSize > 0)
            {
              // Read msgID (first byte of payload)
              packetBuffer.readBytes(&pktInfo.msgID, 1);
              crc = CRC32.crc32_upd(&pktInfo.msgID, 1);
              // do case based on msgID after verification
              if (payloadSize > 1) {
                uint8_t dummy;
                for (size_t i = 1; i < payloadSize; i++) {
                  packetBuffer.pop(dummy);
                  crc = CRC32.crc32_upd(&dummy, 1);
                }
              }
            }
            
            // Read CRC and end marker
            uint8_t footer[5];
            packetBuffer.readBytes(footer, 5);
            pktInfo.crc = footer[0] | (footer[1] << 8) | (footer[2] << 16) | (footer[3] << 24);
            if (footer[4] == END_MARKER)
            {
              pktInfo.isValid = (crc == pktInfo.crc);
              // Print Packet Info Full Struct
              Debug.printf("len: %u, size: %u, seq: %u, sysID: %u, axisID: %u, msgID: 0x%02X, CRC32: 0x%08X, isValid: %s\n",
                           pktInfo.packetLength, payloadSize, pktInfo.sequenceNumber,
                           pktInfo.systemId, pktInfo.axisId, pktInfo.msgID, pktInfo.crc, pktInfo.isValid ? "true" : "false");
            }
            else
            {
              Debug.println("ERROR: Invalid end marker");
              parseState = ParseState::PACKET_ERROR;
            }
          }
        }
        parseState = ParseState::WAITING_START;
      }
    }
  }

  SerialEvent();
}
