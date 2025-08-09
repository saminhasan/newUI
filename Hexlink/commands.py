import zlib
import struct
import numpy as np
from enum import IntEnum

PACKET_OVERHEAD = 16
MIN_PACKET_SIZE = 17  # START(1) + LEN(4) + SEQ(4) + FROM(1) + TO(1) + CRC(4)+ PAYLOAD(1) + END(1)
MAX_PACKET_SIZE = 8192_000 + PACKET_OVERHEAD
START_MARKER = bytes([0x01])
END_MARKER = bytes([0x04])


class MsgID(IntEnum):
    HEARTBEAT = 0x01
    ENABLE = 0x02
    PLAY = 0x03
    PAUSE = 0x04
    STOP = 0x05
    DISABLE = 0x06
    UPLOAD = 0x07
    ACK = 0x08
    NAK = 0x09
    RESET = 0x0A
    QUIT = 0x0B
    CONNECT = 0x0C
    DISCONNECT = 0x0D
    MOVE = 0x0E


# Access as bytes
msg_bytes = {msg: bytes([msg.value]) for msg in MsgID}
# print(msg_bytes)
# Reverse lookup
msgIDs = {v: k.name for k, v in msg_bytes.items()}
# print(msgIDs[bytes([0x01])])


def encode_packet(seq: int, _payload: bytes) -> bytearray:
    if not isinstance(_payload, bytes):
        raise TypeError("Payload must be of type bytes")
    if len(_payload) + PACKET_OVERHEAD > MAX_PACKET_SIZE:
        raise ValueError(f"Payload too large: {len(_payload)} bytes")
    _packet_len = struct.pack("<I", len(_payload) + 16)
    _seq = struct.pack("<I", seq)
    _from_id = b"\xff"
    _to_id = bytes([(1 << 7) | (0 << 6) | (0 << 5) | (0 << 4) | (0 << 3) | (0 << 2) | (0 << 1) | 0])
    crc_input = _packet_len + _seq + _from_id + _to_id + _payload
    _crc = struct.pack("<I", zlib.crc32(crc_input) & 0xFFFFFFFF)
    _raw_packet = bytearray(START_MARKER + _packet_len + _seq + _from_id + _to_id + _crc + _payload + END_MARKER)
    return _raw_packet


def heartbeat(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.HEARTBEAT])


def enable(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.ENABLE])


def play(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.PLAY])


def pause(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.PAUSE])


def stop(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.STOP])


def disable(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.DISABLE])


def reset(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.RESET])


def quit(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.QUIT])


def connect(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.CONNECT])


def disconnect(seq: int) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.DISCONNECT])


def upload(seq: int, array: np.ndarray) -> bytearray:
    if not isinstance(array, np.ndarray):
        raise TypeError("Array must be a NumPy ndarray")
    if array.ndim != 2 or array.shape[1] != 6:
        raise ValueError("Array must have shape (N, 6)")
    float_array = array.astype(np.float32)
    payload_data = float_array.tobytes()
    payload = msg_bytes[MsgID.UPLOAD] + payload_data
    return encode_packet(seq, payload)


def move(seq: int, pose: np.ndarray) -> bytearray:
    if not isinstance(pose, np.ndarray):
        raise TypeError("Pose must be a NumPy ndarray")
    if pose.ndim != 1 or pose.shape[0] != 6:
        raise ValueError("Pose must have shape (6,)")
    float_array = pose.astype(np.float32)
    payload_data = float_array.tobytes()
    payload = msg_bytes[MsgID.MOVE] + payload_data
    return encode_packet(seq, payload)


def ack(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.ACK] + msgID)


def nak(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, msg_bytes[MsgID.NAK] + msgID)


if __name__ == "__main__":
    n = 3
    # Test UPLOAD packet
    data_array = np.arange(n * 6).reshape((n, 6)).astype(np.float32)
    data_packet = upload(1, data_array)
    print(f"Data Packet: {data_packet.hex()}")
