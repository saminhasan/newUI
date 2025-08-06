
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
  digitalWrite(LED_BUILTIN, Serial.dtr() ? HIGH : LOW);
  if (!packetBuffer.isEmpty())
  {
    while (packetBuffer.pop(b))
    {
      Debug.printf(" 0x%02X", b);
    }
    Debug.println();
  }
  SerialEvent();
}
