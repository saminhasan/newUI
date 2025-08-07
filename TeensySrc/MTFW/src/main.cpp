#include "imports.h"
#define Debug SerialUSB1
byte b;
enum class ParseState
{
  AWAIT_START,
  AWAIT_HEADER,
  AWAIT_PAYLOAD,
  PACKET_FOUND,
  PACKET_HANDLING,
  PACKET_ERROR
};
ParseState parseState = ParseState::AWAIT_START;
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
}
void printArray(float arr[][6], size_t length)
{
  for (size_t i = length-1; i < length; i++)
  {
    Debug.printf("%zu : %f %f %f %f %f %f\n", i + 1, arr[i][0], arr[i][1], arr[i][2], arr[i][3], arr[i][4], arr[i][5]);
  }
}

void loop()
{
  serialEvent();

  digitalWrite(LED_BUILTIN, Serial.dtr());

  switch (parseState)
  {
  case ParseState::AWAIT_START:
    if (packetBuffer.popUntil(START_MARKER))
    {
        parseState = ParseState::AWAIT_HEADER;
    }
    break;

  case ParseState::AWAIT_HEADER:
    if (packetBuffer.size() >= 14)
    {
      uint8_t header[14];
      packetBuffer.readBytes(header, 14);
      pktInfo.packetLength = uint32_t(header[0]) | (uint32_t(header[1]) << 8) | (uint32_t(header[2]) << 16) | (uint32_t(header[3]) << 24);
      pktInfo.sequenceNumber = uint32_t(header[4]) | (uint32_t(header[5]) << 8) | (uint32_t(header[6]) << 16) | (uint32_t(header[7]) << 24);
      pktInfo.systemId = header[8];
      pktInfo.axisId = header[9];
      pktInfo.crc = uint32_t(header[10]) | (uint32_t(header[11]) << 8) | (uint32_t(header[12]) << 16) | (uint32_t(header[13]) << 24);
      crc = CRC32.crc32(header, 10);
      pktInfo.payloadSize = pktInfo.packetLength - 16;
      parseState = ParseState::AWAIT_PAYLOAD;
    }
    break;

  case ParseState::AWAIT_PAYLOAD:
    if (packetBuffer.size() >= (pktInfo.payloadSize + 1))
      parseState = ParseState::PACKET_FOUND;
    break;

  case ParseState::PACKET_FOUND:
  {
    for (size_t i = 0; i < pktInfo.payloadSize; i++)
    {
      uint8_t payloadByte = packetBuffer[i];
      crc = CRC32.crc32_upd(&payloadByte, 1);
    }
    pktInfo.isValid = (crc == pktInfo.crc) && (packetBuffer[pktInfo.payloadSize] == END_MARKER) && (pktInfo.payloadSize > 0);
    if (pktInfo.isValid)
    {      packetBuffer.pop(pktInfo.msgID);
      parseState = ParseState::PACKET_HANDLING;

    }
    else
    {
      Debug.println("Invalid packet (CRC or end‐marker mismatch)");
      Debug.printf("len: %u, size: %u, seq: %u, sysID: %u, axisID: %u, msgID: 0x%02X, CRC32: 0x%08X, CRC32: 0x%08X, isValid: %s, end: 0x%u\n",
                   pktInfo.packetLength, pktInfo.payloadSize, pktInfo.sequenceNumber,
                   pktInfo.systemId, pktInfo.axisId, pktInfo.msgID, pktInfo.crc, crc,
                   pktInfo.isValid ? "true" : "false", packetBuffer[pktInfo.payloadSize + 1]);
      parseState = ParseState::AWAIT_START;
      break;
    }
  }
  case ParseState::PACKET_HANDLING:
  {
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
    parseState = ParseState::AWAIT_START;
    break;
  }

  default:
    parseState = ParseState::AWAIT_START;
    break;
  }
}
