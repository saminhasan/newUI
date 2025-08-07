import zlib
import ctypes
import struct
import numpy as np

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
    _packet_len = struct.pack("<I", len(_payload) + 16)
    _seq = struct.pack("<I", ctypes.c_uint32(seq).value)
    _system_id = b"\xff"
    _axis_id = bytes([(1 << 7) | (0 << 6) | (0 << 5) | (0 << 4) | (0 << 3) | (0 << 2) | (0 << 1) | 0])
    crc_input = _packet_len + _seq + _system_id + _axis_id + _payload
    _crc = struct.pack("<I", zlib.crc32(crc_input) & 0xFFFFFFFF)
    _end_marker = b"\x04"
    _raw_packet = bytearray(_start_marker + _packet_len + _seq + _system_id + _axis_id + _payload + _crc + _end_marker)
    # print(f"Packet Size : {len(_raw_packet)} bytes")
    return _raw_packet


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


def data(seq: int, array: np.ndarray) -> bytearray:
    if not isinstance(array, np.ndarray):
        raise TypeError("Array must be a NumPy ndarray")

    if array.ndim != 2 or array.shape[1] != 6:
        raise ValueError("Array must have shape (N, 6)")

    # Convert to float32 and flatten to bytes
    float_array = array.astype(np.float32)
    payload_data = float_array.tobytes()

    # Combine DATA command with the float data
    payload = bytes([DATA.value]) + payload_data

    return create_packet(seq, payload)


if __name__ == "__main__":
    n = 3
    # data_array = np.random.rand(n, 6).astype(np.float32)
    data_array = np.arange(n * 6).reshape((n, 6)).astype(np.float32)
    packet = data(1, data_array)
    print(packet)
