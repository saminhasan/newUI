import zlib
import struct
import numpy as np
from enum import Enum, auto
from typing import Callable, Optional
from Hexlink.commands import START_MARKER, END_MARKER, PACKET_OVERHEAD, MAX_PACKET_SIZE, msgIDs


class ParseState(Enum):
    AWAIT_START = auto()
    AWAIT_HEADER = auto()
    AWAIT_PAYLOAD = auto()
    PACKET_FOUND = auto()
    PACKET_HANDLING = auto()
    PACKET_ERROR = auto()


class Parser:
    def __init__(self, callback: Optional[Callable[[dict], None]] = None):
        """
        callback: fn(frame_dict) called on each valid packet
        """
        self.state = ParseState.AWAIT_START
        self.callback = callback

        # working vars
        self._packet_length: int = 0
        self._sequence: int = 0
        self._from_id: int = 0
        self._to_id: int = 0
        self._crc_expected: int = 0
        self._crc_computed: int = 0
        self._payload_size: int = 0

    def parse(self, buffer: bytearray) -> None:
        """
        Consume as many packets from buffer as possible.
        Returns a list of frame dicts. Leaves any partial packet in buffer.
        """
        frames: list[dict] = []
        header_size: int = PACKET_OVERHEAD - 2  # subtract start+end markers

        while True:
            match self.state:
                case ParseState.AWAIT_START:
                    idx = buffer.find(START_MARKER[0])  # Find single byte, not bytes object
                    if idx < 0:
                        buffer.clear()
                        break
                    if idx > 0:
                        del buffer[:idx]
                    buffer.pop(0)  # Remove the START_MARKER
                    self.state = ParseState.AWAIT_HEADER

                case ParseState.AWAIT_HEADER:
                    # Need: LEN(4) + SEQ(4) + FROM(1) + TO(1) + CRC(4) = 14 bytes
                    if len(buffer) < header_size:
                        break
                    hdr = bytes(buffer[:header_size])
                    self._packet_length = struct.unpack_from("<I", hdr, 0)[0]  # bytes 0-3
                    self._sequence = struct.unpack_from("<I", hdr, 4)[0]  # bytes 4-7
                    self._from_id = hdr[8]  # byte 8
                    self._to_id = hdr[9]  # byte 9
                    self._crc_expected = struct.unpack_from("<I", hdr, 10)[0]  # bytes 10-13
                    # CRC is computed on: LEN + SEQ + FROM + TO + PAYLOAD (as per  encoding)
                    self._crc_computed = zlib.crc32(hdr[:10]) & 0xFFFFFFFF  # LEN + SEQ + FROM + TO
                    # Payload size = total_packet_size - START(1) - LEN(4) - SEQ(4) - FROM(1) - TO(1) - CRC(4) - END(1)
                    # = packet_length - 16 (since packet_length is total size as per Teensy debug)
                    self._payload_size = self._packet_length - PACKET_OVERHEAD
                    del buffer[:14]

                    if self._payload_size < 0:
                        self.state = ParseState.PACKET_ERROR
                    else:
                        self.state = ParseState.AWAIT_PAYLOAD

                case ParseState.AWAIT_PAYLOAD:
                    if len(buffer) < self._payload_size + 1:
                        break
                    self.state = ParseState.PACKET_FOUND

                case ParseState.PACKET_FOUND:
                    payload = bytes(buffer[: self._payload_size])
                    self._crc_computed = zlib.crc32(payload, self._crc_computed) & 0xFFFFFFFF
                    end_marker = buffer[self._payload_size]
                    valid = self._crc_computed == self._crc_expected and end_marker == END_MARKER[0]  # Compare with single byte
                    if valid:
                        _id, payloadDecoded = decodePayload(payload)
                        frame = {
                            "sequence": self._sequence,
                            "from": self._from_id,
                            "to": self._to_id,
                            "msg_id": _id,
                            "payload": payloadDecoded,
                        }
                        frames.append(frame)
                        del buffer[: self._payload_size + 1]  # Remove payload + end marker
                        self.state = ParseState.PACKET_HANDLING

                    else:
                        print(
                            f"Invalid packet: CRC mismatch or wrong end marker. Expected CRC: {self._crc_expected:08x}, Computed: {self._crc_computed:08x}, End marker: 0x{end_marker:02x}"
                        )
                        del buffer[: self._payload_size + 1]
                        self.state = ParseState.PACKET_ERROR

                case ParseState.PACKET_HANDLING:
                    if self.callback:
                        self.callback([frame])
                    self.state = ParseState.AWAIT_START

                case ParseState.PACKET_ERROR:
                    print("[Parser.parse] : Dropping Packet")
                    self.state = ParseState.AWAIT_START

                case _:  # default case
                    self.state = ParseState.AWAIT_START


def decodePayload(payload):
    if not isinstance(payload, bytes):
        raise TypeError("Payload must be of type bytes")
    _id = msgIDs.get(bytes([payload[0]]), "UNKNOWN")
    match _id:
        case "UNKNOWN":
            decodedPayload = None
        case "HEARTBEAT":
            decodedPayload = "HEARTBEAT"
        case "ENABLE":
            decodedPayload = "ENABLE"
        case "PLAY":
            decodedPayload = "PLAY"
        case "PAUSE":
            decodedPayload = "PAUSE"
        case "STOP":
            decodedPayload = "STOP"
        case "DISABLE":
            decodedPayload = "DISABLE"
        case "ACK":
            decodedPayload = msgIDs.get(bytes([payload[1]]), "UNKNOWN")
        case "NAK":
            decodedPayload = msgIDs.get(bytes([payload[1]]), "UNKNOWN")
        case "RESET":
            decodedPayload = "RESET"
        case "QUIT":
            decodedPayload = "QUIT"
        case "CONNECT":
            decodedPayload = "CONNECT"
        case "DISCONNECT":
            decodedPayload = "DISCONNECT"
        case "UPLOAD" | "MOVE":
            decodedPayload = np.frombuffer(payload[1:], dtype=np.float32).reshape(-1, 6)
        case "INFO":
            decodedPayload = payload[1:].decode("utf-8")
        case _:
            decodedPayload = payload[1:]  # Default case, return raw payload
    # print(f"Decoded payload: {_id}, Data: {decodedPayload}")
    return _id, decodedPayload
