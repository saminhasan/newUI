#ifndef PACKET_PARSER_H
#define PACKET_PARSER_H

#include <stdint.h>
#include <cstring>
#include <FastCRC.h>
#include "constants.h"
#include "globals.h"
#include "RingBuffer.h"
#include "messages.h"
#include "delf.h"

enum class ParseState {
    AWAIT_START,
    AWAIT_HEADER,
    AWAIT_PAYLOAD_CRC,
    PACKET_COMPLETE
};

struct PacketInfo {
    uint32_t length;
    uint32_t sequence;
    size_t   payloadSize;
    uint8_t  from;
    uint8_t  to;
    uint8_t  msgID;
    bool     isValid;

    PacketInfo():
        length(0),
        sequence(0),
        payloadSize(0),
        from(0),
        to(0),
        msgID(0),
        isValid(false)
    {}
};

struct PacketParserState {
    // 4-byte fields first
    ParseState state;        // 4 bytes
    FastCRC32  crc32;        // 4-byte aligned
    uint32_t   runningCRC;
    uint32_t   packetLength;
    uint32_t   sequence;
    uint32_t   crcExpected;
    size_t     payloadSize;       // 4
    size_t     payloadBytesRead;  // 4
    elapsedMicros elapsedTime;    // uint32_t wrapper
    PacketInfo parsedPacket;

    // pointers
    RingBuffer* ringBuffer;
    void (*packetCallback)(const PacketInfo&);

    // small scalars
    uint8_t fromID;
    uint8_t toID;
    uint8_t msgID;
    bool    crcInitialized;

    // temp buffer
    uint8_t tempBuffer[TEMP_BUFFER_SIZE];

    PacketParserState(RingBuffer& rb)
        : state(ParseState::AWAIT_START),
          crc32(),
          runningCRC(0),
          packetLength(0),
          sequence(0),
          crcExpected(0),
          payloadSize(0),
          payloadBytesRead(0),
          elapsedTime(0),
          parsedPacket(),
          ringBuffer(&rb),
          packetCallback(nullptr),
          fromID(0),
          toID(0),
          msgID(0),
          crcInitialized(false)
    {}
};

// ---- CRC helpers ----
inline void initCRC(PacketParserState& s) {
    s.runningCRC = 0;
    s.crcInitialized = false;
}

inline void updateCRC(PacketParserState& s, const uint8_t* data, size_t len) {
    if (!s.crcInitialized) {
        s.runningCRC = s.crc32.crc32(data, len);
        s.crcInitialized = true;
    } else {
        s.runningCRC = s.crc32.crc32_upd(data, len);
    }
}

inline void updateCRC(PacketParserState& s, uint8_t b) {
    updateCRC(s, &b, 1);
}

// ---- Payload handlers ----
typedef void (*MsgHandler)(PacketParserState&, const uint8_t*, size_t);

inline void handleACK(PacketParserState& s, const uint8_t* buf, size_t len) {
    if (s.payloadBytesRead == 0 && len > 0) {
        request = s.msgID;
        response = buf[0];
    }
}

inline void handleNAK(PacketParserState& s, const uint8_t* buf, size_t len) {
    handleACK(s, buf, len); // same wire format
}

inline void handleMOVE(PacketParserState& s, const uint8_t* buf, size_t len) {
    size_t copyLen = (s.payloadBytesRead + len <= ROW_SIZE) ? len : (ROW_SIZE - s.payloadBytesRead);
    memcpy(reinterpret_cast<uint8_t*>(MoveData) + s.payloadBytesRead, buf, copyLen);
}

inline void handleUPLOAD_commit(PacketParserState& s) {
    request = s.msgID;
    arrayLength = s.payloadSize / ROW_SIZE; // number of rows
}

inline void handleSimple(PacketParserState& s, const uint8_t*, size_t) {
    request = s.msgID;
}

// Called only *after* CRC is verified OK
inline void handleFEEDBACK_commit(PacketParserState& s) {
    request = s.msgID;
}

// ---- Dispatch table ----
static MsgHandler msgHandlers[MAX_MSG_ID + 1];

inline void initMsgHandlers() {
    for (size_t i = 0; i <= MAX_MSG_ID; i++) {
        msgHandlers[i] = handleSimple;
    }
    msgHandlers[msgID::ACK]      = handleACK;
    msgHandlers[msgID::NAK]      = handleNAK;
    msgHandlers[msgID::MOVE]     = handleMOVE;
    // UPLOAD + FEEDBACK get final commit after CRC; during stream we still update CRC / copy.
}

// ---- Core Parse Function ----
inline void parsePacket(PacketParserState& s) {
    RingBuffer& ring = *s.ringBuffer;

    switch (s.state) {
    case ParseState::AWAIT_START: {
        if (ring.readBytesUntil(START_MARKER)) {
            if (!ring.isEmpty()) {
                initCRC(s);
                updateCRC(s, START_MARKER);
                s.state = ParseState::AWAIT_HEADER;
                s.elapsedTime = 0;
            }
        }
        break;
    }

    case ParseState::AWAIT_HEADER: {
        if (ring.size() < HEADER_SIZE) return;

        uint8_t headerBytes[HEADER_SIZE];
        ring.readBytes(headerBytes, HEADER_SIZE);
        updateCRC(s, headerBytes, HEADER_SIZE);

        memcpy(&s.packetLength, &headerBytes[LEN_OFFSET], LEN_SIZE);
        memcpy(&s.sequence,     &headerBytes[SEQ_OFFSET], SEQ_SIZE);
        s.fromID = headerBytes[FROM_OFFSET];
        s.toID   = headerBytes[TO_OFFSET];
        s.msgID  = headerBytes[MSG_ID_OFFSET];

        s.payloadSize      = s.packetLength - PACKET_OVERHEAD;
        s.payloadBytesRead = 0;

        if ((PACKET_OVERHEAD > s.packetLength) || (s.packetLength > MAX_PACKET_SIZE)) {
            s.state = ParseState::AWAIT_START;
            return;
        }

        // Optional but useful: enforce exact FEEDBACK size
        if (s.msgID == msgID::FEEDBACK && s.payloadSize != sizeof(feedback)) {
            s.state = ParseState::AWAIT_START; // drop malformed
            return;
        }

        s.state = ParseState::AWAIT_PAYLOAD_CRC;
        break;
    }

    case ParseState::AWAIT_PAYLOAD_CRC: {
        size_t remaining = s.payloadSize - s.payloadBytesRead;

        if (s.msgID == msgID::UPLOAD) {
            size_t n = ring.readBytes(dataBuffer.bytes + s.payloadBytesRead, remaining);
            if (n > 0) {
                updateCRC(s, dataBuffer.bytes + s.payloadBytesRead, n);
                s.payloadBytesRead += n;
            }
        }
        else if (s.msgID == msgID::FEEDBACK) {
            size_t available = ring.size();
            size_t toRead    = (remaining < available) ? remaining : available;
            if (toRead > 0) {
                size_t n = ring.readBytes(reinterpret_cast<uint8_t*>(&feedback) + s.payloadBytesRead, toRead);
                if (n > 0) {
                    updateCRC(s, reinterpret_cast<uint8_t*>(&feedback) + s.payloadBytesRead, n);
                    s.payloadBytesRead += n;
                }
            }
        }
        else {
            size_t available = ring.size();
            size_t toRead    = (remaining < available) ? remaining : available;
            if (toRead > TEMP_BUFFER_SIZE) toRead = TEMP_BUFFER_SIZE; // clamp BEFORE read
            if (toRead > 0) {
                size_t n = ring.readBytes(s.tempBuffer, toRead);
                updateCRC(s, s.tempBuffer, n);

                if (s.msgID <= MAX_MSG_ID) {
                    MsgHandler handler = msgHandlers[s.msgID];
                    if (handler) handler(s, s.tempBuffer, n);
                }

                s.payloadBytesRead += n;
            }
        }

        if (s.payloadBytesRead == s.payloadSize && ring.size() >= CRC_SIZE) {
            uint8_t crcBytes[CRC_SIZE];
            ring.readBytes(crcBytes, CRC_SIZE);
            memcpy(&s.crcExpected, crcBytes, CRC_SIZE);

            // Build parsedPacket
            s.parsedPacket.sequence    = s.sequence;
            s.parsedPacket.from        = s.fromID;
            s.parsedPacket.to          = s.toID;
            s.parsedPacket.length      = s.packetLength;
            s.parsedPacket.msgID       = s.msgID;
            s.parsedPacket.payloadSize = s.payloadSize;
            s.parsedPacket.isValid     = (s.runningCRC == s.crcExpected);

            // Only mutate globals on valid CRC
            if (s.parsedPacket.isValid)
             {
                if (s.msgID == msgID::UPLOAD)   handleUPLOAD_commit(s);
                if (s.msgID == msgID::FEEDBACK) handleFEEDBACK_commit(s);

            }

            s.state = ParseState::PACKET_COMPLETE;
        }
        break;
    }

    case ParseState::PACKET_COMPLETE: {
        if (s.parsedPacket.isValid && s.packetCallback) {
            s.packetCallback(s.parsedPacket);
        }

        // logInfo(Serial,
        //         "MsgID=%s | Length=%u bytes | Time=%lu us | Throughput=%.2f MB/s\n",
        //         msgID_toStr(s.parsedPacket.msgID),
        //         s.parsedPacket.length,
        //         s.elapsedTime,
        //         (s.parsedPacket.length * 1e6f) / (s.elapsedTime * 1024.0f * 1024.0f));

        s.state = ParseState::AWAIT_START;
        break;
    }
    }
}

struct PacketParser {
    PacketParserState state;
    PacketParser(RingBuffer& rb, void (*cb)(const PacketInfo&)=nullptr)
        : state(rb)
    {
        state.packetCallback = cb;
        initMsgHandlers();
    }

    void setCallback(void (*cb)(const PacketInfo&)) { state.packetCallback = cb; }
    void parse() { parsePacket(state); }
    PacketInfo& lastPacket() { return state.parsedPacket; }
};

#endif // PACKET_PARSER_H
