from multiprocessing import Process, Pipe, Queue
from queue import Empty
from threading import Thread, Event
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo
import time
import serial
from collections import deque


def portList() -> list[ListPortInfo]:
    return list_ports.comports()


class serialServer:
    def __init__(self, pipe, recvQ=None):
        self.pipe = pipe
        self.recvQ = recvQ

        self.running: bool = True
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.portStr: str = ""
        self.filePath: str = ""

        # Initialize these in run() method to avoid pickling issues
        self.senderThread = None
        self._listen_evt = None
        self._listener_thread = None
        self.byteBuffer = Queue()

    @property
    def connected(self) -> bool:
        return self.port is not None and self.port.is_open

    def connect(self):
        if not self.portStr:
            return False
        try:
            self.port.open()
            # if self._listen_evt:
            #     self._listen_evt.set()
            print(f"connect to port: {self.portStr}")
            return True
        except Exception as e:
            print(f"Error opening port: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            return True
        # if self._listen_evt:
        #     self._listen_evt.clear()
        try:
            self.port.close()
        except Exception as e:
            print(f"Error closing port: {e}")
            return False
        print(f"Disconnected from port: {self.portStr}")
        return True

    def SerialRequestSender(self):
        print("SerialRequestSender thread started.")
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
                status = self.disconnect()
                if status and self.listen:
                    self.listen.clear()

            if request["event"] == "upload":
                self.filePath = request["filePath"]
                print(f"{self.filePath=}")
            if request["event"] == "quit":  # Handle additional quit logic from here such as sending stop signal to teensy
                self.running = False
                self.listen.clear()
            response = request
            response["status"] = "ACK" if status else "NAK"
            self.pipe.send(response)
            # print(f"Response sent: {response}")
        print("sendRequest thread stopped.")

    def SerialListener(self):
        byteBuffer = bytearray()  # bytes returned from serial read is immutable, so we use bytearray for mutability
        print("Listener thread started.")
        while self.running:
            self.listen.wait()
            while self.running and self.listen.is_set():
                if self.connected:
                    try:
                        rawBytes = self.port.read(max(self.port.in_waiting, 1))
                    except Exception as e:
                        print(f"Serial read error: {e}")
                        continue
                    if len(rawBytes) == 0:
                        continue
                    byteBuffer.extend(rawBytes)
                    parts = byteBuffer.split(b"\n")
                    for part in parts[:-1]:
                        if self.running and self.listen.is_set():
                            self.recvQ.put({"INFO": part.decode("utf-8", errors="ignore") + "\n"})
                            drop = len(part) + 1
                            del byteBuffer[:drop]
                        else:
                            print("Listener stopped while processing data.")
                            return
        print("Listener thread stopped.")

    def run(self):
        print("Serial server started.")
        self.listen = Event()
        self.rsT = Thread(target=self.SerialRequestSender, name="SerialRequestSender", daemon=True)
        self.slT = Thread(target=self.SerialListener, name="SerialListener", daemon=True)
        self.rsT.start()
        self.slT.start()
        self.rsT.join()
        self.slT.join()
        self.stop()
        print("Serial server stopped.")
        exit(0)

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
