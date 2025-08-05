import ctypes

HEARTBEAT = ctypes.c_uint8(0x01)
ENABLE = ctypes.c_uint8(0x02)
DISABLE = ctypes.c_uint8(0x03)
PLAY = ctypes.c_uint8(0x04)
PAUSE = ctypes.c_uint8(0x05)
STOP = ctypes.c_uint8(0x06)
DATA = ctypes.c_uint8(0x07)


def foo(data: bytes) -> bytearray:
    packetLength = bytes(len(data))
    startByte = 0xAA
    return bytearray([startByte, packetLength]) + data
