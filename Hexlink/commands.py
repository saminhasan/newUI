import zlib
import ctypes
import struct
import numpy as np

START_MARKER = bytes([0x01])
END_MARKER = bytes([0x04])
PACKET_OVERHEAD = 16
MAX_PACKET_SIZE = 8192 * 1000 + PACKET_OVERHEAD
HEARTBEAT = bytes([0x01])
ENABLE = bytes([0x02])
PLAY = bytes([0x03])
PAUSE = bytes([0x04])
STOP = bytes([0x05])
DISABLE = bytes([0x06])
DATA = bytes([0x07])
ACK = bytes([0x08])
NAK = bytes([0x09])
RESET = bytes([0x0A])
QUIT = bytes([0x0B])
CONNECT = bytes([0x0C])
DISCONNECT = bytes([0x0D])
# reverse the kv pairs
msgIDs = {
    HEARTBEAT: "HEARTBEAT",
    ENABLE: "ENABLE",
    PLAY: "PLAY",
    PAUSE: "PAUSE",
    STOP: "STOP",
    DISABLE: "DISABLE",
    DATA: "DATA",
    ACK: "ACK",
    NAK: "NAK",
    RESET: "RESET",
    QUIT: "QUIT",
    CONNECT: "CONNECT",
    DISCONNECT: "DISCONNECT",
}


def encode_packet(seq: int, _payload: bytes) -> bytearray:
    if not isinstance(_payload, bytes):
        raise TypeError("Payload must be of type bytes")
    _packet_len = struct.pack("<I", len(_payload) + 16)
    # print(f"size: {len(_payload) + 16}")
    _seq = struct.pack("<I", ctypes.c_uint32(seq).value)
    _from_id = b"\xff"
    _to_id = bytes([(1 << 7) | (0 << 6) | (0 << 5) | (0 << 4) | (0 << 3) | (0 << 2) | (0 << 1) | 0])
    crc_input = _packet_len + _seq + _from_id + _to_id + _payload
    _crc = struct.pack("<I", zlib.crc32(crc_input) & 0xFFFFFFFF)
    _raw_packet = bytearray(START_MARKER + _packet_len + _seq + _from_id + _to_id + _crc + _payload + END_MARKER)
    # print(f"Packet Size : {len(_raw_packet)} bytes")
    return _raw_packet


def decode_packet(packet: bytearray) -> dict:
    if not isinstance(packet, (bytes, bytearray)):
        return {"isValid": False, "error": "Invalid packet type"}
    if (
        len(packet) < 16
    ):  # Minimum packet size: start(1) + len(4) + seq(4) + from(1) + to(1) + crc(4) + end(1) = 16 bytes minimum
        return {"isValid": False, "error": "Packet too short"}
    try:
        # Parse packet components
        _start_marker = packet[0:1]
        _packet_len_bytes = packet[1:5]
        _seq_bytes = packet[5:9]
        _from_id = packet[9:10]
        _to_id = packet[10:11]
        _crc_bytes = packet[11:15]
        _end_marker = packet[-1:]
        _payload = packet[15:-1]

        # Unpack binary data
        packet_len = struct.unpack("<I", _packet_len_bytes)[0]
        seq = struct.unpack("<I", _seq_bytes)[0]
        received_crc = struct.unpack("<I", _crc_bytes)[0]

        # Validate packet structure
        is_valid = True
        error_msg = None

        if _start_marker != b"\x01":
            is_valid = False
            error_msg = "Invalid start marker"
        elif _end_marker != b"\x04":
            is_valid = False
            error_msg = "Invalid end marker"
        elif len(packet) != packet_len + 6:  # +6 for start marker (1) + packet_len field (4) + end marker (1)
            is_valid = False
            error_msg = f"Packet length mismatch: expected {packet_len + 6}, got {len(packet)}"

        # Validate CRC if requested and packet structure is valid
        calculated_crc = None
        if is_valid:
            crc_input = _packet_len_bytes + _seq_bytes + _from_id + _to_id + _payload
            calculated_crc = zlib.crc32(crc_input) & 0xFFFFFFFF
            if calculated_crc != received_crc:
                is_valid = False
                error_msg = "CRC validation failed"

        # Reconstruct payload based on message type
        reconstructed_payload = None
        message_type = None

        if len(_payload) > 0:
            message_type = _payload[0]

            if message_type == HEARTBEAT:
                reconstructed_payload = {"event": "HEARTBEAT"}
            elif message_type == ENABLE:
                reconstructed_payload = {"event": "ENABLE"}
            elif message_type == PLAY:
                reconstructed_payload = {"event": "PLAY"}
            elif message_type == PAUSE:
                reconstructed_payload = {"event": "PAUSE"}
            elif message_type == STOP:
                reconstructed_payload = {"event": "STOP"}
            elif message_type == DISABLE:
                reconstructed_payload = {"event": "DISABLE"}
            elif message_type == DATA:
                # Reconstruct numpy array from DATA payload
                if len(_payload) > 1:
                    float_data = _payload[1:]  # Skip the command byte
                    if len(float_data) % 4 == 0:  # Valid float32 data
                        float_count = len(float_data) // 4
                        if float_count % 6 == 0:  # Valid (N, 6) array
                            n_rows = float_count // 6
                            float_array = np.frombuffer(float_data, dtype=np.float32)
                            reconstructed_payload = {
                                "event": "DATA",
                                "array": float_array.reshape((n_rows, 6)),
                                "shape": (n_rows, 6),
                            }
                        else:
                            reconstructed_payload = {
                                "event": "DATA",
                                "error": f"Invalid float count {float_count}, not divisible by 6",
                            }
                    else:
                        reconstructed_payload = {
                            "event": "DATA",
                            "error": f"Invalid data length {len(float_data)}, not divisible by 4",
                        }
                else:
                    reconstructed_payload = {"event": "DATA", "error": "No data payload"}
            elif message_type == ACK:
                reconstructed_payload = {"event": "ACK"}
            elif message_type == NAK:
                reconstructed_payload = {"event": "NAK"}
            elif message_type == RESET:
                reconstructed_payload = {"event": "RESET"}
            elif message_type == QUIT:
                reconstructed_payload = {"event": "QUIT"}
            elif message_type == CONNECT:
                reconstructed_payload = {"event": "CONNECT"}
            elif message_type == DISCONNECT:
                reconstructed_payload = {"event": "DISCONNECT"}

            else:
                reconstructed_payload = {"event": "UNKNOWN", "message_id": message_type}

        return {
            "isValid": is_valid,
            "error": error_msg,
            "start_marker": _start_marker,
            "packet_len": packet_len,
            "seq": seq,
            "system_id": _from_id,
            "axis_id": _to_id,
            "crc": received_crc,
            "calculated_crc": calculated_crc if is_valid else None,
            "raw_payload": _payload,
            "payload": reconstructed_payload,
            "message_type": message_type,
            "end_marker": _end_marker,
            "raw_packet": packet,
        }

    except Exception as e:
        return {"isValid": False, "error": f"Decode error: {str(e)}"}


def heartbeat(seq: int) -> bytearray:
    return encode_packet(seq, HEARTBEAT)


def enable(seq: int) -> bytearray:
    return encode_packet(seq, ENABLE)


def play(seq: int) -> bytearray:
    return encode_packet(seq, PLAY)


def pause(seq: int) -> bytearray:
    return encode_packet(seq, PAUSE)


def stop(seq: int) -> bytearray:
    return encode_packet(seq, STOP)


def disable(seq: int) -> bytearray:
    return encode_packet(seq, DISABLE)


def reset(seq: int) -> bytearray:
    return encode_packet(seq, RESET)


def quit(seq: int) -> bytearray:
    return encode_packet(seq, QUIT)


def connect(seq: int) -> bytearray:
    return encode_packet(seq, CONNECT)


def disconnect(seq: int) -> bytearray:
    return encode_packet(seq, DISCONNECT)


def data(seq: int, array: np.ndarray) -> bytearray:
    if not isinstance(array, np.ndarray):
        raise TypeError("Array must be a NumPy ndarray")
    if array.ndim != 2 or array.shape[1] != 6:
        raise ValueError("Array must have shape (N, 6)")
    float_array = array.astype(np.float32)
    payload_data = float_array.tobytes()
    payload = DATA + payload_data
    return encode_packet(seq, payload)


def ack(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, ACK + msgID)


def nak(seq: int, msgID: bytes) -> bytearray:
    return encode_packet(seq, NAK + msgID)


if __name__ == "__main__":
    n = 3
    # Test DATA packet
    data_array = np.arange(n * 6).reshape((n, 6)).astype(np.float32)
    data_packet = data(1, data_array)
    data_decoded = decode_packet(data_packet)
    print("DATA packet:")
    print(f"  Valid: {data_decoded['isValid']}")
    print(f"  Event: {data_decoded['payload']['event']}")
    print(f"  Array shape: {data_decoded['payload']['shape']}")
    print(f"  Array values:\n{data_decoded['payload']['array']}")
    print()

    # Test HEARTBEAT packet
    hb_packet = heartbeat(2)
    hb_decoded = decode_packet(hb_packet)
    print("HEARTBEAT packet:")
    print(f"  Valid: {hb_decoded['isValid']}")
    print(f"  Error: {hb_decoded['error']}")
    print(f"  Raw payload: {hb_decoded['raw_payload']}")
    print(f"  Message type: {hb_decoded['message_type']}")
    if hb_decoded["payload"]:
        print(f"  Event: {hb_decoded['payload']['event']}")
    print()

    # Test ENABLE packet
    enable_packet = enable(3)
    enable_decoded = decode_packet(enable_packet)
    print("ENABLE packet:")
    print(f"  Valid: {enable_decoded['isValid']}")
    if enable_decoded["payload"]:
        print(f"  Event: {enable_decoded['payload']['event']}")
    print()
