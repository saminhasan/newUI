
#include "imports.h"
#define Debug SerialUSB1
byte b;

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
void printArray(float arr[][6], size_t length)
{
  for (size_t i = 0; i < length; i++)
  {
    Debug.printf("%zu : %f %f %f %f %f %f\n", i + 1,
                 arr[i][0], arr[i][1], arr[i][2],
                 arr[i][3], arr[i][4], arr[i][5]);
                 delayMicroseconds(10);
  }
}

void loop()
{
  // 1) Always pull in any new bytes
  serialEvent();

  // 2) Update LED to reflect DTR state (non-blocking)
  digitalWrite(LED_BUILTIN, Serial.dtr());

  // 3) State‐machine dispatch: only one packet stage per call
  switch (parseState)
  {
  case ParseState::WAITING_START:
    while (packetBuffer.pop(b))
    {
      if (b == START_MARKER)
      {
        parseState = ParseState::WAITING_HEADER;
        break;
      }
    }
    break;

  case ParseState::WAITING_HEADER:
    if (packetBuffer.size() >= 10)
    {
      uint8_t header[10];
      packetBuffer.readBytes(header, 10);
      pktInfo.packetLength = uint32_t(header[0]) | (uint32_t(header[1]) << 8) | (uint32_t(header[2]) << 16) | (uint32_t(header[3]) << 24);
      pktInfo.sequenceNumber = uint32_t(header[4]) |(uint32_t(header[5]) << 8) |(uint32_t(header[6]) << 16) | (uint32_t(header[7]) << 24);

      pktInfo.systemId = header[8];
      pktInfo.axisId = header[9];
      // payload = [ msgID (1 byte) + actual data... ]
      pktInfo.payloadSize = pktInfo.packetLength - 16;
      crc = CRC32.crc32(header, 10);
      parseState = ParseState::WAITING_PAYLOAD;
    }
    break;

  case ParseState::WAITING_PAYLOAD:
    if (packetBuffer.size() >= (pktInfo.payloadSize + 5))
    {
      parseState = ParseState::PACKET_FOUND;
    }
    break;

  case ParseState::PACKET_FOUND:
  {
    pktInfo.crc = packetBuffer[pktInfo.payloadSize] |(packetBuffer[pktInfo.payloadSize + 1] << 8) |(packetBuffer[pktInfo.payloadSize + 2] << 16) |(packetBuffer[pktInfo.payloadSize + 3] << 24);

    for (size_t i = 0; i < pktInfo.payloadSize; i++)
    {
      uint8_t payloadByte = packetBuffer[i];
      crc = CRC32.crc32_upd(&payloadByte, 1);
    }
    uint8_t endMarker = packetBuffer[pktInfo.payloadSize + 4];
    pktInfo.isValid = (crc == pktInfo.crc) && (endMarker == END_MARKER) && (pktInfo.payloadSize > 0);
    if (!pktInfo.isValid)
    {
      Debug.println("Invalid packet (CRC or end‐marker mismatch)");
      Debug.printf("len: %u, size: %u, seq: %u, sysID: %u, axisID: %u, msgID: 0x%02X, CRC32: 0x%08X, CRC32: 0x%08X, isValid: %s\n",
                   pktInfo.packetLength, pktInfo.payloadSize, pktInfo.sequenceNumber,
                   pktInfo.systemId, pktInfo.axisId, pktInfo.msgID, pktInfo.crc, crc,
                   pktInfo.isValid ? "true" : "false");
      parseState = ParseState::WAITING_START;
      break;
    }
    packetBuffer.pop(pktInfo.msgID);
    switch (pktInfo.msgID)
    {
    case msgID::HEARTBEAT:
      Debug.println("HEARTBEAT received");
      break;
    case msgID::ENABLE:
      Debug.println("ENABLE received");
      break;
    case msgID::PLAY:
      Debug.println("PLAY received");
      break;
    case msgID::PAUSE:
      Debug.println("PAUSE received");
      break;
    case msgID::STOP:
      Debug.println("STOP received");
      break;
    case msgID::DISABLE:
      Debug.println("DISABLE received");
      break;
    case msgID::DATA:
    {
      // payload bytes = [msgID][float data...]
      size_t dataBytes = pktInfo.payloadSize;
      arrayLength = dataBytes / (6 * sizeof(float));
      if (arrayLength > maxArrayLength)
        Debug.printf("Error: arrayLength %u > max %u\n", arrayLength, maxArrayLength);
      else
      {
        // copy only the actual float data (skip index 0 which was msgID)
        packetBuffer.readBytes(db.bytes, pktInfo.payloadSize);
        Debug.printf("DATA: %u rows\n", arrayLength);
        printArray(db.data, arrayLength);
      }
      break;
    }
    default:
      Debug.printf("Unknown msgID: 0x%02X\n", pktInfo.msgID);
      break;
    }
    parseState = ParseState::WAITING_START;
    break;
  }
  default:
    parseState = ParseState::WAITING_START;
    break;
  }
}
