import zlib
import ctypes
import struct

HEARTBEAT = ctypes.c_uint8(0x01)
ENABLE = ctypes.c_uint8(0x02)
PLAY = ctypes.c_uint8(0x03)
PAUSE = ctypes.c_uint8(0x04)
STOP = ctypes.c_uint8(0x05)
DISABLE = ctypes.c_uint8(0x06)
DATA = ctypes.c_uint8(0x07)


def create_packet(seq: int, _payload: bytes) -> bytearray:
    if not isinstance(_payload, bytes):
        raise TypeError("Payload must be of type bytes")

    _start_marker = b"\x01"
    _payload_len = struct.pack("<I", len(_payload))
    _seq = struct.pack("<I", ctypes.c_uint32(seq).value)
    _system_id = b"\xff"
    _axis_id = bytes([(1 << 7) | (0 << 6) | (0 << 5) | (0 << 4) | (0 << 3) | (0 << 2) | (0 << 1) | 0])
    crc_input = _start_marker + _payload_len + _seq + _system_id + _axis_id + _payload
    _crc = struct.pack("<I", zlib.crc32(crc_input) & 0xFFFFFFFF)
    _end_marker = b"\x04"
    return bytearray(_start_marker + _payload_len + _seq + _system_id + _axis_id + _payload + _crc + _end_marker)


def heartbeat(seq: int) -> bytearray:
    return create_packet(seq, bytes([HEARTBEAT.value]))


def enable(seq: int) -> bytearray:
    return create_packet(seq, bytes([ENABLE.value]))


def play(seq: int) -> bytearray:
    return create_packet(seq, bytes([PLAY.value]))


def pause(seq: int) -> bytearray:
    return create_packet(seq, bytes([PAUSE.value]))


def stop(seq: int) -> bytearray:
    return create_packet(seq, bytes([STOP.value]))


def disable(seq: int) -> bytearray:
    return create_packet(seq, bytes([DISABLE.value]))


if __name__ == "__main__":
    payload = bytes([HEARTBEAT.value])
    packet = create_packet(1, payload)
