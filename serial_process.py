from multiprocessing import Process, Pipe, Queue
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
            if request["event"] == "quit":
                self.running = False
                if self._listen_evt:
                    self._listen_evt.set()
                    """
                    as soon as the _listener_thread is started, the inside the first loop, it gets blocked by the wait() call.

                    when the event is set, the listener thread will continue reading from the serial port(ser.read is blocking).

                     
                    """
                    return

            # move the logics below to a proper location later
            response = request
            response["status"] = "ACK" if status else "NAK"
            self.conn.send(response)
            print("LOOPING")

    def handleResponse(self, response):
        pass

    def _listener_loop(self):
        print("Listener thread started.")
        byte_buf = deque()  # holds individual characters until we hit '\n'
        out_batch = []  # list of dicts ready to send in one go
        while self.running:
            self._listen_evt.wait()  # block until set()
            while self.running and self._listen_evt.is_set():
                if not self.connected:
                    print("Port is not connected, cannot read data.")
                    self._listen_evt.clear()
                try:
                    # read whatever's waiting (or at least 1 byte)
                    toRead = self.port.in_waiting or 1
                except Exception as e:
                    print(f"Serial read error: {e}")
                    break
                raw = self.port.read(toRead)  # returns bytes
                text = raw.decode("utf-8", errors="ignore")
                # push each char into the deque, flush whenever we see '\n'
                for ch in text:
                    byte_buf.append(ch)
                    if ch == "\n":
                        line = "".join(byte_buf)
                        out_batch.append({"INFO": line})
                        byte_buf.clear()

                # if we have any complete lines, send them as a batch
                if len(out_batch) > 5:
                    if self.recvQ:
                        self.recvQ.put(out_batch)
                    out_batch = []

        print("Listener thread stopped.")

    def run(self):
        print("Serial server started.")
        # Initialize threading objects here to avoid pickling issues
        self.senderThread = Thread(target=self.sendRequest, name="SerialSender", daemon=True)
        self._listen_evt = Event()
        self._listener_thread = Thread(target=self._listener_loop, name="SerialListener", daemon=True)

        try:
            self.senderThread.start()
            self._listener_thread.start()
            self.senderThread.join()  # Wait for sender thread to finish
        except Exception as e:
            print(f"Error in serialServer: {e}")
        finally:
            self.stop()

    def stop(self):
        if self.connected:
            self.disconnect()
        if self.recvQ:
            self.recvQ.put({"event": "quit"})

        if self.conn and self.conn.closed is False:
            self.conn.send({"event": "quit"})
        if self.senderThread and self.senderThread.is_alive():
            self.senderThread.join()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join()
        print("Serial server stopped.")


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
