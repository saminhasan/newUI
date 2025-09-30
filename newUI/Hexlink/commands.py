import struct
import numpy as np
from zlib import crc32
from enum import IntEnum

START_MARKER = b"\x01"

START_SIZE = 1
LEN_SIZE = 4
SEQ_SIZE = 4
FROM_SIZE = 1
TO_SIZE = 1
MSG_ID_SIZE = 1
CRC_SIZE = 4
PACKET_OVERHEAD = START_SIZE + LEN_SIZE + SEQ_SIZE + FROM_SIZE + TO_SIZE + MSG_ID_SIZE + CRC_SIZE
MIN_PACKET_SIZE = PACKET_OVERHEAD
MAX_PACKET_SIZE = 16 * 1024 * 1024 + PACKET_OVERHEAD


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
    FEEDBACK = 0x0F
    INFO = 0xFD
    UNKNOWN = 0xFE


# Access as bytes
msg_bytes = {msg: bytes([msg.value]) for msg in MsgID}
# print(msg_bytes, msg_bytes[MsgID.HEARTBEAT])
# Reverse lookup
msgIDs = {v: k.name for k, v in msg_bytes.items()}
# print(msgIDs[bytes([0x01])])


def encode_packet(seq: int, _msg_id: bytes, _payload: bytes = b"") -> bytearray:
    if not isinstance(seq, int) or not (0 <= seq <= 0xFFFFFFFF):
        raise TypeError("Sequence must be an integer between 0 and 0xFFFFFFFF")
    if not isinstance(_msg_id, bytes) or len(_msg_id) != 1:
        raise TypeError("Message ID must be a single byte")
    if not isinstance(_payload, bytes):
        raise TypeError("Payload must be of type bytes")
    if len(_payload) + PACKET_OVERHEAD > MAX_PACKET_SIZE:
        raise ValueError(f"Payload too large: {len(_payload)} bytes")
    _packet_len = struct.pack("<I", len(_payload) + PACKET_OVERHEAD) if _payload else struct.pack("<I", PACKET_OVERHEAD)
    _seq = struct.pack("<I", seq)
    _from_id = b"\xff"
    _to_id = bytes([(1 << 7) | (0 << 6) | (0 << 5) | (0 << 4) | (0 << 3) | (0 << 2) | (0 << 1) | 0])
    # _to_id = b"\x00"
    crc_input = START_MARKER + _packet_len + _seq + _from_id + _to_id + _msg_id + _payload
    _crc = struct.pack("<I", crc32(crc_input))
    _raw_packet = bytearray(START_MARKER + _packet_len + _seq + _from_id + _to_id + _msg_id + _payload + _crc)
    return _raw_packet


def heartbeat(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.HEARTBEAT])


def enable(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.ENABLE])


def play(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.PLAY])


def pause(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.PAUSE])


def stop(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.STOP])


def disable(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.DISABLE])


def reset(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.RESET])


def quit(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.QUIT])


def connect(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.CONNECT])


def disconnect(seq: int) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.DISCONNECT])


def upload(seq: int, array: np.ndarray) -> bytearray:
    if not isinstance(array, np.ndarray):
        raise TypeError("Array must be a NumPy ndarray")
    if array.ndim != 2 or array.shape[1] != 6:
        raise ValueError("Array must have shape (N, 6)")
    float_array = array.astype(np.float32)
    payload_data = float_array.tobytes()
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.UPLOAD], _payload=payload_data)


def move(seq: int, pose: np.ndarray) -> bytearray:
    if not isinstance(pose, np.ndarray):
        raise TypeError("Pose must be a NumPy ndarray")
    if pose.ndim != 1 or pose.shape[0] != 6:
        raise ValueError("Pose must have shape (6,)")
    float_array = pose.astype(np.float32)
    payload_data = float_array.tobytes()
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.MOVE], _payload=payload_data)


def ack(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.ACK], _payload=msgID)


def nak(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, _msg_id=msg_bytes[MsgID.NAK], _payload=msgID)


if __name__ == "__main__":
    n = 3
    # Test UPLOAD packet
    data_array = np.arange(n * 6).reshape((n, 6)).astype(np.float32)
    data_packet = upload(1, data_array)
    print(f"Data Packet: {data_packet.hex()}")

    # Test ACK packet
    ack_packet = ack(1, msgID=msg_bytes[MsgID.UPLOAD])
    print(f"ACK Packet: {ack_packet.hex()}")

    # Test NAK packet
    nak_packet = nak(1, msgID=msg_bytes[MsgID.UPLOAD])
    print(f"NAK Packet: {nak_packet.hex()}")

    # Test Heartbeat packet
    heartbeat_packet = heartbeat(1)
    print(f"Heartbeat Packet: {heartbeat_packet.hex()}")
