from enum import Enum, auto
import struct
import zlib
from typing import Callable, Optional
from Hexlink.commands import START_MARKER, END_MARKER, PACKET_OVERHEAD, MAX_PACKET_SIZE, msgIDs

# These should already be defined in your module:
# START_MARKER = 0x01
# END_MARKER   = 0x04   # or whatever your end-marker is
# PACKET_OVERHEAD = header_bytes + start + end  # e.g. 16
# MAX_PACKET_SIZE  = <your maximum allowed packet length>


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
        self._packet_length = 0
        self._sequence = 0
        self._from_id = 0
        self._to_id = 0
        self._crc_expected = 0
        self._crc_computed = 0
        self._payload_size = 0

    def parse(self, buffer: bytearray) -> list[dict]:
        """
        Consume as many packets from buffer as possible.
        Returns a list of frame dicts. Leaves any partial packet in buffer.
        """
        frames = []
        header_size = PACKET_OVERHEAD - 2  # subtract start+end markers

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
                    if len(buffer) < 14:
                        break
                    hdr = bytes(buffer[:14])
                    self._packet_length = struct.unpack_from("<I", hdr, 0)[0]  # bytes 0-3
                    self._sequence = struct.unpack_from("<I", hdr, 4)[0]  # bytes 4-7
                    self._from_id = hdr[8]  # byte 8
                    self._to_id = hdr[9]  # byte 9
                    self._crc_expected = struct.unpack_from("<I", hdr, 10)[0]  # bytes 10-13

                    # CRC is computed on: LEN + SEQ + FROM + TO + PAYLOAD (as per your encoding)
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
                        frame = {
                            "sequence": self._sequence,
                            "from": self._from_id,
                            "to": self._to_id,
                            "crc": self._crc_expected,
                            "msg_id": payload[0] if payload else None,
                            "msg_name": msgIDs.get(bytes([payload[0]]), "UNKNOWN"),
                            "payload": payload,
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
                        for f in frames:
                            self.callback(f)
                    # for f in frames:
                    #     print(f)
                    self.state = ParseState.AWAIT_START

                case ParseState.PACKET_ERROR:
                    self.state = ParseState.AWAIT_START

                case _:  # default case
                    self.state = ParseState.AWAIT_START

        return frames
