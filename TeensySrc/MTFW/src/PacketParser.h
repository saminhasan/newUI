#ifndef PACKET_PARSER_H
#define PACKET_PARSER_H

#include <stdint.h>
#include <stddef.h>

// Packet structure constants
#define START_MARKER 0x01
#define END_MARKER 0x04
#define PACKET_HEADER_SIZE 11  // start + len + seq + sys + axis
#define PACKET_FOOTER_SIZE 5   // crc + end
#define MIN_PACKET_SIZE 16     // header + footer (no payload)

enum class ParseState {
    READ_WAIT,
    READ_LENGTH,
    READ_SEQ,
    READ_SYS_ID,
    READ_AXIS_ID,
    READ_PAYLOAD,
    READ_CRC,
    READ_END,
    PACKET_COMPLETE,
    PACKET_ERROR
};

struct ParsedPacket {
    uint32_t payloadLength;
    uint32_t sequenceNumber;
    uint8_t systemId;
    uint8_t axisId;
    uint8_t* payload;
    uint32_t crc;
    bool isValid;
    
    ParsedPacket() : payloadLength(0), sequenceNumber(0), systemId(0), 
                     axisId(0), payload(nullptr), crc(0), isValid(false) {}
};

class PacketParser {
private:
    ParseState state;
    uint8_t buffer[4];  // Temp buffer for multi-byte fields
    size_t bufferIndex;
    size_t payloadBytesRead;
    ParsedPacket currentPacket;
    uint8_t* payloadBuffer;
    size_t maxPayloadSize;
    
    uint32_t bytesToUint32(const uint8_t* bytes) {
        return bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24);
    }
    
public:
    PacketParser(uint8_t* payloadBuf, size_t maxPayloadSz) 
        : state(ParseState::READ_WAIT), bufferIndex(0), payloadBytesRead(0),
          payloadBuffer(payloadBuf), maxPayloadSize(maxPayloadSz) {}
    
    bool processByte(uint8_t byte) {
        switch (state) {
            case ParseState::READ_WAIT:
                if (byte == START_MARKER) {
                    state = ParseState::READ_LENGTH;
                    bufferIndex = 0;
                    currentPacket = ParsedPacket();
                }
                break;
                
            case ParseState::READ_LENGTH:
                buffer[bufferIndex++] = byte;
                if (bufferIndex >= 4) {
                    currentPacket.payloadLength = bytesToUint32(buffer);
                    if (currentPacket.payloadLength > maxPayloadSize) {
                        state = ParseState::PACKET_ERROR;
                        return false;
                    }
                    state = ParseState::READ_SEQ;
                    bufferIndex = 0;
                }
                break;
                
            case ParseState::READ_SEQ:
                buffer[bufferIndex++] = byte;
                if (bufferIndex >= 4) {
                    currentPacket.sequenceNumber = bytesToUint32(buffer);
                    state = ParseState::READ_SYS_ID;
                }
                break;
                
            case ParseState::READ_SYS_ID:
                currentPacket.systemId = byte;  // Accept any system ID
                state = ParseState::READ_AXIS_ID;
                break;
                
            case ParseState::READ_AXIS_ID:
                currentPacket.axisId = byte;    // Accept any axis ID
                if (currentPacket.payloadLength > 0) {
                    state = ParseState::READ_PAYLOAD;
                    payloadBytesRead = 0;
                    currentPacket.payload = payloadBuffer;
                } else {
                    state = ParseState::READ_CRC;
                    bufferIndex = 0;
                }
                break;
                
            case ParseState::READ_PAYLOAD:
                payloadBuffer[payloadBytesRead++] = byte;
                if (payloadBytesRead >= currentPacket.payloadLength) {
                    state = ParseState::READ_CRC;
                    bufferIndex = 0;
                }
                break;
                
            case ParseState::READ_CRC:
                buffer[bufferIndex++] = byte;
                if (bufferIndex >= 4) {
                    currentPacket.crc = bytesToUint32(buffer);
                    state = ParseState::READ_END;
                }
                break;
                
            case ParseState::READ_END:
                if (byte == END_MARKER) {
                    currentPacket.isValid = true;
                    state = ParseState::PACKET_COMPLETE;
                    return true;  // Packet complete
                } else {
                    state = ParseState::PACKET_ERROR;
                    return false;
                }
                break;
                
            default:
                state = ParseState::READ_WAIT;
                break;
        }
        return false;  // Packet not yet complete
    }
    
    const ParsedPacket& getPacket() const {
        return currentPacket;
    }
    
    void reset() {
        state = ParseState::READ_WAIT;
        bufferIndex = 0;
        payloadBytesRead = 0;
    }
    
    ParseState getState() const {
        return state;
    }
};

#endif // PACKET_PARSER_H
