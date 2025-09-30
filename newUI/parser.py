import zlib
import struct
import numpy as np
from enum import Enum, auto
from collections import deque
from typing import Callable, Optional
from Hexlink.commands import (
    START_MARKER,
    PACKET_OVERHEAD,
    MAX_PACKET_SIZE,
    msgIDs,
    LEN_SIZE,
    SEQ_SIZE,
    FROM_SIZE,
    TO_SIZE,
    MSG_ID_SIZE,
    CRC_SIZE,
    START_SIZE,
)


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
        self._msg_id: int = 0
        self._crc_expected: int = 0
        self._crc_computed: int = 0
        self._payload_size: int = 0
        self.frames: deque[dict] = deque()

    def parse(self, buffer: bytearray) -> None:
        """
        Consume as many packets from buffer as possible.
        Returns a list of frame dicts. Leaves any partial packet in buffer.
        """

        while True:
            match self.state:
                case ParseState.AWAIT_START:
                    idx = buffer.find(START_MARKER[0])  # Find single byte, not bytes object
                    if idx < 0:
                        buffer.clear()
                        break
                    if idx > 0:
                        del buffer[:idx]
                    self.state = ParseState.AWAIT_HEADER

                case ParseState.AWAIT_HEADER:
                    # Need: START(1) + LEN(4) + SEQ(4) + FROM(1) + TO(1) + MSG_ID(1) = 12 bytes minimum
                    if len(buffer) < 12:
                        break
                    start_marker = buffer[0]  # Should be START_MARKER[0]
                    self._packet_length = struct.unpack_from("<I", buffer, 1)[0]  # bytes 1-4
                    self._sequence = struct.unpack_from("<I", buffer, 5)[0]  # bytes 5-8
                    self._from_id = buffer[9]  # byte 9
                    self._to_id = buffer[10]  # byte 10
                    self._msg_id = buffer[11]  # byte 11

                    self._payload_size = self._packet_length - PACKET_OVERHEAD

                    if self._payload_size < 0 or self._packet_length < PACKET_OVERHEAD:
                        self.state = ParseState.PACKET_ERROR
                    else:
                        self.state = ParseState.AWAIT_PAYLOAD

                case ParseState.AWAIT_PAYLOAD:
                    if len(buffer) < self._packet_length:
                        break
                    self.state = ParseState.PACKET_FOUND

                case ParseState.PACKET_FOUND:
                    # Extract payload and CRC
                    payload_start = 12  # START(1) + LEN(4) + SEQ(4) + FROM(1) + TO(1) + MSG_ID(1)
                    payload_end = payload_start + self._payload_size
                    crc_start = payload_end

                    payload = bytes(buffer[payload_start:payload_end])
                    self._crc_expected = struct.unpack_from("<I", buffer, crc_start)[0]
                    crc_input = bytes(buffer[:crc_start])  # Everything up to but not including CRC
                    self._crc_computed = zlib.crc32(crc_input) & 0xFFFFFFFF

                    valid = self._crc_computed == self._crc_expected
                    if valid:
                        full_payload = bytes([self._msg_id]) + payload
                        _id, payloadDecoded = decodePayload(full_payload)
                        frame = {
                            "sequence": self._sequence,
                            "from": self._from_id,
                            "to": self._to_id,
                            "msg_id": _id,
                            "payload": payloadDecoded,
                        }
                        self.frames.append(frame)
                        del buffer[: self._packet_length]
                        self.state = ParseState.PACKET_HANDLING

                    else:
                        print(
                            f"Invalid packet: CRC mismatch. Expected CRC: {self._crc_expected:08x}, Computed: {self._crc_computed:08x}"
                        )
                        # Remove entire packet from buffer
                        del buffer[: self._packet_length]
                        self.state = ParseState.PACKET_ERROR

                case ParseState.PACKET_HANDLING:
                    if self.callback:
                        # Call callback with current frames and then clear them
                        self.callback(list(self.frames))
                        self.frames.clear()
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
        case "FEEDBACK":
            decodedPayload = parse_feedback(payload)
        case _:
            decodedPayload = payload[1:]  # Default case, return raw payload
    # print(f"Decoded payload: {_id}, Data: {decodedPayload}")
    return _id, decodedPayload


def parse_feedback(payload: bytes) -> dict:

    # ---- fixed layout from your packed C struct ----
    FEEDBACK = struct.Struct("<4B f 2I 8s 8s")  # axisId, mode, armed, calibrated, setPoint, tSend, tRecv, sent[8], recv[8]
    if len(payload) < 1 + FEEDBACK.size:
        raise ValueError(f"payload too short: need {1 + FEEDBACK.size} bytes, got {len(payload)}")

    axisId, mode, armed, calibrated, setPoint, tSend, tRecv, sent, recv = FEEDBACK.unpack_from(payload, 1)

    # ---- helpers (all local so this stays self-contained) ----
    def _u32delta(a, b):  # micros() wrap-safe delta
        return (a - b) & 0xFFFFFFFF

    def _s8(u):  # 0..255 -> -128..127
        return u - 256 if u > 127 else u

    def _u32_le(b4):  # bytes[4] -> uint32
        return int.from_bytes(b4[:4], "little", signed=False)

    def _i32_le(b4):  # bytes[4] -> int32
        return int.from_bytes(b4[:4], "little", signed=True)

    def _f32_le(b4):  # bytes[4] -> float32
        return struct.unpack("<f", b4[:4])[0]

    # ---- enums / names (from your header) ----
    CMD_NAME = {
        0x91: "START_MOTOR",
        0x92: "STOP_MOTOR",
        0x93: "TORQUE_CONTROL",
        0x94: "SPEED_CONTROL",
        0x95: "POSITION_CONTROL",
        0x97: "STOP_CONTROL",
    }
    RES_NAME = {
        0x00: "SUCCESS",
        0x01: "FAIL",
        0x02: "FAIL_UNKNOWN_CMD",
        0x03: "FAIL_UNKNOWN_ID",
        0x04: "FAIL_RO_REG",
        0x05: "FAIL_UNKNOWN_REG",
        0x06: "FAIL_STR_FORMAT",
        0x07: "FAIL_DATA_FORMAT",
        0x0B: "FAIL_WO_REG",
        0x80: "FAIL_NOT_CONNECTED",
    }
    CONTROL_CMDS = {0x93, 0x94, 0x95}
    # per-command location of result byte (your C varies!)
    RES_IDX = {
        0x81: 1,
        0x82: 1,
        0x83: 3,
        0x84: 3,
        0x91: 1,
        0x92: 1,
        0x93: 1,
        0x94: 1,
        0x95: 1,
        0x96: 1,
        0x97: 1,
        0xA1: 3,
        0xA2: 2,
        0xB1: 1,
        0xB2: 1,
        0xB3: 1,
        0xB4: 2,
    }
    FAULT_BITS = {
        0x01: "FREQ_TOO_HIGH",
        0x02: "OV",
        0x04: "UV",
        0x08: "OT",
        0x10: "START_FAIL",
        0x40: "OC",
        0x80: "SOFTWARE_EXCEPTION",
    }

    # ---- base fields (keep original keys for drop-in compatibility) ----
    out = {
        "axisId": axisId,
        "mode": mode,
        "armed": bool(armed),
        "calibrated": bool(calibrated),
        "setPoint": setPoint,
        "tSend": tSend,
        "tRecv": tRecv,
        "latency_us": _u32delta(tRecv, tSend),
        # keep simple forms AND nicer hex strings
        "sent": list(sent),  # list of ints 0..255
        "recv": list(recv),  # list of ints 0..255
    }

    # ---- TX/RX meta ----
    tx_cmd = sent[0] if len(sent) else None
    rx_cmd = recv[0] if len(recv) else None
    out["tx"] = {
        "cmd": tx_cmd,
        "cmd_name": CMD_NAME.get(tx_cmd),
    }
    out["rx"] = {
        "cmd": rx_cmd,
        "cmd_name": CMD_NAME.get(rx_cmd),
    }

    # ---- resolve result code with per-command index rules ----
    if rx_cmd is not None:
        idx = RES_IDX.get(rx_cmd, 1)
        rx_res = recv[idx] if len(recv) > idx else None
        out["rx"]["res"] = rx_res
        out["rx"]["res_name"] = RES_NAME.get(rx_res)
        out["ok"] = (rx_res == 0x00) if rx_res is not None else None
    else:
        out["rx"]["res"] = None
        out["rx"]["res_name"] = None
        out["ok"] = None

    # ---- deep decode per command ----
    decoded = None

    if rx_cmd in CONTROL_CMDS and len(recv) == 8:
        # Mirror your MCResControl math exactly
        temp = _s8(recv[2])
        pos_u16 = recv[3] | (recv[4] << 8)
        position_rad = (pos_u16 * 25.0 / 65535.0) - 12.5

        speed_12 = ((recv[5] << 4) | (recv[6] >> 4)) & 0x0FFF
        speed_rad_s = (speed_12 * 130.0 / 4095.0) - 65.0

        torque_12 = (((recv[6] & 0x0F) << 8) | recv[7]) & 0x0FFF
        KT = 0.116670
        GEAR = 9.0
        torque_nm = (torque_12 * (450.0 * KT * GEAR) / 4095.0) - (225.0 * KT * GEAR)

        decoded = {
            "temperature_C": temp,
            "position_rad": position_rad,
            "speed_rad_s": speed_rad_s,
            "torque_Nm": torque_nm,
        }

    # Attach decoded (if any)
    out["rx"]["decoded"] = decoded

    return out


def print_feedback_line(out):
    # always show axis + armed
    axis = out.get("axisId")
    armed = 1 if out.get("armed") else 0

    rx = out.get("rx", {})
    cmd = rx.get("cmd")
    res = rx.get("res")
    ok = res == 0

    # units for the setpoint based on control cmd
    sp_unit = {0x93: " N·m", 0x94: " rad/s", 0x95: " rad"}.get(cmd, "")

    # base line
    line = f"AXIS {axis} (armed={armed})"

    # if it's a control reply *and* success, dump telemetry
    dec = rx.get("decoded") if ok else None
    if cmd in (0x93, 0x94, 0x95) and dec:
        setp = out.get("setPoint")
        pos = dec.get("position_rad")
        vel = dec.get("speed_rad_s")
        trq = dec.get("torque_Nm")
        line += f" | setPoint={setp:.6g}{sp_unit} | position={pos:.6g} rad | velocity={vel:.6g} rad/s | torque={trq:.6g} N·m"
    else:
        # non-control reply (or failure) — show cmd/result briefly
        cmd_name = rx.get("cmd_name") or (f"0x{cmd:02X}" if cmd is not None else "?")
        res_name = rx.get("res_name") or (f"{res}" if res is not None else "?")
        line += f" | rx={cmd_name} ({res_name})"

    print(line)


def main():
    """Comprehensive test suite for the parser"""
    from Hexlink.commands import encode_packet, MsgID, msg_bytes

    def run_test(test_name, test_func):
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print("=" * 50)
        try:
            result = test_func()
            if result:
                print(f" {test_name} PASSED")
            else:
                print(f" {test_name} FAILED")
            return result
        except Exception as e:
            print(f" {test_name} FAILED with exception: {e}")
            return False

    def test_single_packet():
        """Test parsing a single packet"""
        seq = 1234
        msg_id = msg_bytes[MsgID.HEARTBEAT]
        payload = b"test payload"

        encoded_packet = encode_packet(seq, msg_id, payload)
        print(f"Encoded packet: {encoded_packet.hex()}")

        # Decode packet structure for verification
        packet_len = struct.unpack("<I", encoded_packet[1:5])[0]
        seq_decoded = struct.unpack("<I", encoded_packet[5:9])[0]
        print(f"Packet length: {packet_len}, Sequence: {seq_decoded}")

        received_frames = []

        def callback(frames):
            received_frames.extend(frames)

        parser = Parser(callback)
        buffer = bytearray(encoded_packet)
        parser.parse(buffer)

        if len(received_frames) != 1:
            print(f"Expected 1 frame, got {len(received_frames)}")
            return False

        frame = received_frames[0]
        print(f"Received: seq={frame['sequence']}, msg={frame['msg_id']}, payload={frame['payload']}")

        assert frame["sequence"] == seq, f"Sequence mismatch: expected {seq}, got {frame['sequence']}"
        assert frame["msg_id"] == "HEARTBEAT", f"Message ID mismatch"
        return True

    def test_multiple_message_types():
        """Test different message types and payloads"""
        test_cases = [
            (MsgID.HEARTBEAT, b"", "HEARTBEAT"),
            (MsgID.INFO, b"Hello World", "Hello World"),
            (MsgID.ENABLE, b"", "ENABLE"),
            (MsgID.PLAY, b"", "PLAY"),
            (MsgID.PAUSE, b"", "PAUSE"),
            (MsgID.STOP, b"", "STOP"),
            (MsgID.DISABLE, b"", "DISABLE"),
        ]

        for msg_type, payload, expected in test_cases:
            seq = 1000 + msg_type.value
            msg_id = msg_bytes[msg_type]

            encoded_packet = encode_packet(seq, msg_id, payload)

            received_frames = []

            def callback(frames):
                received_frames.extend(frames)

            parser = Parser(callback)
            buffer = bytearray(encoded_packet)
            parser.parse(buffer)

            if len(received_frames) != 1:
                print(f" {msg_type.name}: Expected 1 frame, got {len(received_frames)}")
                return False

            frame = received_frames[0]
            print(f"{msg_type.name}: seq={frame['sequence']}, payload='{frame['payload']}'")

            if frame["sequence"] != seq:
                print(f" {msg_type.name}: Sequence mismatch")
                return False
            if frame["msg_id"] != msg_type.name:
                print(f" {msg_type.name}: Message ID mismatch")
                return False
            if frame["payload"] != expected:
                print(f" {msg_type.name}: Payload mismatch: expected '{expected}', got '{frame['payload']}'")
                return False

        return True

    def test_multiple_packets_in_buffer():
        """Test parsing multiple packets from a single buffer"""
        packets_data = [
            (100, MsgID.HEARTBEAT, b"", "HEARTBEAT"),
            (101, MsgID.ENABLE, b"", "ENABLE"),
            (102, MsgID.INFO, b"Test message", "Test message"),
            (103, MsgID.PLAY, b"", "PLAY"),
            (104, MsgID.STOP, b"", "STOP"),
        ]

        # Create combined buffer
        combined_buffer = bytearray()
        for seq, msg_type, payload, _ in packets_data:
            packet = encode_packet(seq, msg_bytes[msg_type], payload)
            combined_buffer.extend(packet)

        print(f"Combined buffer: {len(combined_buffer)} bytes")

        received_frames = []

        def callback(frames):
            received_frames.extend(frames)
            print(f"Callback received {len(frames)} frames")

        parser = Parser(callback)
        parser.parse(combined_buffer)

        if len(received_frames) != len(packets_data):
            print(f" Expected {len(packets_data)} frames, got {len(received_frames)}")
            return False

        for i, (expected_seq, expected_msg_type, _, expected_payload) in enumerate(packets_data):
            frame = received_frames[i]
            print(f"Frame {i+1}: seq={frame['sequence']}, msg={frame['msg_id']}, payload='{frame['payload']}'")

            if frame["sequence"] != expected_seq:
                print(f" Frame {i+1}: Sequence mismatch")
                return False
            if frame["msg_id"] != expected_msg_type.name:
                print(f" Frame {i+1}: Message type mismatch")
                return False
            if frame["payload"] != expected_payload:
                print(f" Frame {i+1}: Payload mismatch")
                return False

        return True

    def test_partial_packets():
        """Test handling of partial packets in buffer"""
        seq = 500
        msg_id = msg_bytes[MsgID.INFO]
        payload = b"Partial test message"

        encoded_packet = encode_packet(seq, msg_id, payload)

        # Split packet in half
        split_point = len(encoded_packet) // 2
        first_part = encoded_packet[:split_point]
        second_part = encoded_packet[split_point:]

        print(f"Full packet ({len(encoded_packet)} bytes): {encoded_packet.hex()}")
        print(f"First part ({len(first_part)} bytes): {first_part.hex()}")
        print(f"Second part ({len(second_part)} bytes): {second_part.hex()}")

        received_frames = []

        def callback(frames):
            received_frames.extend(frames)
            print(f"Callback received {len(frames)} frames")

        parser = Parser(callback)

        # Send first part - should not produce any frames
        buffer1 = bytearray(first_part)
        print(f"Parsing first part, buffer size: {len(buffer1)}")
        parser.parse(buffer1)
        print(f"After first part: parser state = {parser.state}, buffer remaining = {len(buffer1)}")

        if len(received_frames) != 0:
            print(f" Expected 0 frames after first part, got {len(received_frames)}")
            return False

        # Send second part - should complete the packet
        # Need to combine remaining buffer with second part
        buffer1.extend(second_part)
        print(f"Combined buffer size: {len(buffer1)}")
        parser.parse(buffer1)
        print(f"After second part: parser state = {parser.state}, buffer remaining = {len(buffer1)}")

        if len(received_frames) != 1:
            print(f"Expected 1 frame after second part, got {len(received_frames)}")
            return False

        frame = received_frames[0]
        print(f"Completed frame: seq={frame['sequence']}, msg={frame['msg_id']}, payload='{frame['payload']}'")

        if frame["sequence"] != seq:
            print(" Sequence mismatch in partial packet test")
            return False

        return True

    def test_crc_validation():
        """Test CRC validation with corrupted packet"""
        seq = 999
        msg_id = msg_bytes[MsgID.HEARTBEAT]
        payload = b""

        encoded_packet = encode_packet(seq, msg_id, payload)

        # Corrupt the packet by changing one byte in the middle
        corrupted_packet = bytearray(encoded_packet)
        corrupted_packet[8] = 0x99  # Corrupt sequence byte

        print(f"Original:  {encoded_packet.hex()}")
        print(f"Corrupted: {corrupted_packet.hex()}")

        received_frames = []

        def callback(frames):
            received_frames.extend(frames)

        parser = Parser(callback)
        buffer = bytearray(corrupted_packet)
        parser.parse(buffer)

        # Should receive no frames due to CRC mismatch
        if len(received_frames) != 0:
            print(f" Expected 0 frames due to CRC error, got {len(received_frames)}")
            return False

        print("CRC validation correctly rejected corrupted packet")
        return True

    # Run all tests
    tests = [
        ("Single Packet Test", test_single_packet),
        ("Multiple Message Types Test", test_multiple_message_types),
        ("Multiple Packets in Buffer Test", test_multiple_packets_in_buffer),
        ("Partial Packets Test", test_partial_packets),
        ("CRC Validation Test", test_crc_validation),
    ]

    print("Starting Parser Test Suite")
    print(f"Testing with Python parser against C++ ground truth protocol")

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print(f"\n{'='*60}")
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("All tests PASSED! Parser is working correctly!")
    else:
        print(f" {total - passed} tests FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
