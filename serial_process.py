import time
import serial
from collections import deque
from queue import Empty
from threading import Thread, Event
from multiprocessing import Queue
from Hexlink.commands import *
from more_itertools import chunked
from parser import Parser

np.set_printoptions(precision=6, suppress=True)


class serialServer:
    def __init__(self, pipe):
        self.pipe = pipe
        self.running: bool = True
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.portStr: str = ""
        self.filePath: str = ""
        self.byteBuffer = Queue()
        self.sequence = 1000
        # self.parser = Parser(callback=lambda frame: self.handle_frame(frame))

    @property
    def connected(self) -> bool:
        return self.port is not None and self.port.is_open

    def connect(self):
        if not self.portStr:
            return False
        try:
            self.port.open()
            if not self.listen.is_set():
                self.listen.set()
            print(f"connect to port: {self.portStr}")
            return True
        except Exception as e:
            print(f"Error opening port: {e}")
            return False

    def sendData(self, data: bytes):
        if not self.connected:
            print("Not connected to any port.")
            return False
        try:
            for chunk in chunked(data, 512):
                self.port.write(bytes(chunk))
            return True
        except serial.SerialException as e:
            print(f"Error sending data: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            return True
        if self.listen.is_set():
            self.listen.clear()
        try:
            self.port.close()
        except Exception as e:
            print(f"Error closing port: {e}")
            return False
        print(f"Disconnected from port: {self.portStr}")
        return True

    def SerialRequestSender(self):
        while self.running:
            request = self.pipe.recv()
            status = False
            if request["event"] == "portSelect":
                self.portStr = request["port"]
                self.port.port = self.portStr
                print(f"{self.portStr=}")

            if request["event"] == "connect":
                status = self.connect()
                if status and self.listen:
                    self.listen.set()

            if request["event"] == "disconnect":
                self.sendData(disconnect(self.sequence))
                self.sequence += 1
                status = self.disconnect()
                if status and self.listen:
                    self.listen.clear()
            if request["event"] == "enable":
                self.sendData(enable(self.sequence))
                self.sequence += 1

            if request["event"] == "upload":
                self.filePath = request["filePath"]
                # print(f"{self.filePath=}")
                data_array = np.arange(self.sequence * 6).reshape((self.sequence, 6)).astype(np.float32) + 1
                self.sendData(data(self.sequence, data_array))
                self.sequence += 1

            if request["event"] == "play":
                self.sendData(play(self.sequence))
                self.sequence += 1

            if request["event"] == "pause":
                self.sendData(pause(self.sequence))
                self.sequence += 1

            if request["event"] == "stop":
                self.sendData(stop(self.sequence))
                self.sequence += 1

            if request["event"] == "estop":
                self.sendData(disable(self.sequence))
                self.sequence += 1
                # send stop signal to teensy
                status = self.disconnect()
                if status and self.listen:
                    self.listen.clear()
                pass

            if request["event"] == "reset":
                self.sendData(reset(self.sequence))
                self.sequence += 1
                status = self.disconnect()
                if status and self.listen:
                    self.listen.clear()

            if request["event"] == "quit":  # Handle additional quit logic from here such as sending stop signal to teensy
                self.sendData(quit(self.sequence))
                self.sequence += 1
                self.running = False
                self.listen.set()
                self.listen.clear()

            # Should be done onRecieve from Teensy
            response = request
            response["status"] = "ACK" if status else "NAK"
            try:
                self.pipe.send(response)
            except BrokenPipeError:
                print("Broken pipe error: Pipe is closed.")
                self.running = False
                self.listen.set()
                self.listen.clear()
            except Exception as e:
                print(f"Error sending response: {e}")

    def SerialListener(self):
        byteBuffer = bytearray()  # bytes returned from serial read is immutable, so we use bytearray for mutability
        while self.running:
            self.listen.wait()
            while self.running and self.listen.is_set():
                try:
                    if not (self.connected and (rawBytes := self.port.read(max(self.port.in_waiting, PACKET_OVERHEAD + 1)))):
                        continue
                    byteBuffer.extend(rawBytes)
                    print(" In Buffer : ")
                    for b in byteBuffer:
                        print(f"0x{b:02x}", end=" ")
                    print()
                    frames = self.parser.parse(byteBuffer)
                    # for frame in frames:
                    #     print(frame)

                except serial.SerialException as e:
                    self.disconnect()
                    self.listen.clear()
                    print(f"Serial error: {e}")

                except Exception as e:
                    print(f"Exception: {e}")

    def handle_frame(self, frame):
        print(f"Handling frame: {frame}")

    def run(self):
        print("Serial server started.")
        self.parser = Parser(callback=lambda frame: self.handle_frame(frame))
        self.listen = Event()
        self.rsT = Thread(target=self.SerialRequestSender, name="SerialRequestSender", daemon=True)
        self.slT = Thread(target=self.SerialListener, name="SerialListener", daemon=True)
        self.rsT.start()
        self.slT.start()
        self.rsT.join()
        self.slT.join()
        self.stop()
        print("Serial server stopped.")
        # exit(0)

    def stop(self):
        if self.connected:
            self.disconnect()
        if self.rsT.is_alive():
            self.rsT.join()
        self.pipe.close()
        if self.slT.is_alive():
            self.slT.join()


if __name__ == "__main__":
    pass
