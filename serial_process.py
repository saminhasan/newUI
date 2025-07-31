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
    def __init__(self, conn, recvQ=None):
        self.conn = conn  # This is the child end of the pipe
        self.running: bool = True
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.portStr: str = ""
        self.recvQ = recvQ
        self.filePath: str = ""

        # Initialize these in run() method to avoid pickling issues
        self.senderThread = None
        self._listen_evt = None
        self._listener_thread = None

        self.byte_buf = Queue()

    @property
    def connected(self) -> bool:
        return self.port is not None and self.port.is_open

    def connect(self):
        if not self.portStr:
            return False
        try:
            self.port.open()
            if self._listen_evt:
                self._listen_evt.set()
            print(f"Connected to port: {self.portStr}")
            return True
        except Exception as e:
            print(f"Error opening port: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            return True
        if self._listen_evt:
            self._listen_evt.clear()
        try:
            self.port.close()
        except Exception as e:
            print(f"Error closing port: {e}")
            return False
        print(f"Disconnected from port: {self.portStr}")
        return True

    def sendRequest(self):
        print("Sender thread started.")
        while self.running:
            request = self.conn.recv()
            status = False
            if request["event"] == "portSelect":
                self.portStr = request["port"]
                self.port.port = self.portStr
                print(f"{self.portStr=}")
            if request["event"] == "connect":
                status = self.connect()
                if status and self._listen_evt:
                    self._listen_evt.set()
            if request["event"] == "disconnect":
                status = self.disconnect()
                if status and self._listen_evt:
                    self._listen_evt.clear()

            if request["event"] == "upload":
                self.filePath = request["filePath"]
                print(f"{self.filePath=}")
            if request["event"] == "quit":  # Handle additional quit logic from here such as sending stop signal to teensy
                self.running = False
                self.conn.send({"event": "quit"})

                if self._listen_evt:
                    self._listen_evt.set()  # add counterintuitive explanantion here
                print("Sender thread stopped.")
                return

            # move the logics below to a proper location later
            response = request
            response["status"] = "ACK" if status else "NAK"
            self.conn.send(response)
            print(f"Response sent: {response}")

    def _listener_loop(self):
        print("Listener thread started.")
        lines = []
        # holds individual characters until we hit '\n'
        while self.running:
            self._listen_evt.wait()  # block until set()
            while self.running and self._listen_evt.is_set():
                if not self.connected:
                    print("Port is not connected, cannot read data.")
                    self._listen_evt.clear()
                    continue
                try:
                    rawBytes = self.port.read(max(self.port.in_waiting, 1))
                    for byte in rawBytes:
                        self.byte_buf.put(byte)
                except Exception as e:
                    print(f"Serial read error: {e}")
                    break
                buf = bytearray()
                while True:
                    try:
                        buf.append(self.byte_buf.get(False))
                    except Empty:
                        break
                parts = buf.split(b"\n")
                for part in parts[:-1]:
                    lines.append({"INFO": (part + b"\n").decode("utf-8")})
                tail = parts[-1]
                for b in tail:
                    self.byte_buf.put(b)
                if len(lines) > 100:
                    self.recvQ.put(lines)
                    lines = []
        self.recvQ.put([{"event": "quit"}])
        print("Listener thread stopped.")

    def run(self):
        print("Serial server started.")
        # Initialize threading objects here to avoid pickling issues
        self.senderThread = Thread(target=self.sendRequest, name="SerialSender", daemon=True)
        self._listen_evt = Event()
        self._listener_thread = Thread(target=self._listener_loop, name="SerialListener", daemon=True)
        self.senderThread.start()
        self._listener_thread.start()
        self.senderThread.join()  # Wait for the sender thread to finish
        self._listener_thread.join()  # Wait for the listener thread to finish
        self.stop()
        print("Serial server stopped.")

    def stop(self):
        # 4.1 Close serial port if still open
        if self.connected:
            self.disconnect()

        # 4.2 Join threads with a timeout
        if self.senderThread.is_alive():
            self.senderThread.join()
        if self._listener_thread.is_alive():
            self._listener_thread.join()

        # 4.3 Close IPC
        self.conn.close()


if __name__ == "__main__":
    # parent_conn, child_conn = Pipe()
    # ss = serialServer(child_conn)
    # ssp = Process(target=ss.run)
    # ssp.start()
    # parent_conn.send({"event": "test", "data": "Hello, World!"})
    # time.sleep(1)  # Allow some time for processing
    # if parent_conn.poll():
    #     response = parent_conn.recv()
    #     print(f"Received response: {response}")
    # parent_conn.send({"event": "quit"})
    # ssp.join()
    # parent_conn.close()
    # child_conn.close()
    pass
