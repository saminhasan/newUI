import os
import time
import serial
import serial.threaded
from parser import Parser
from Hexlink.commands import *
from multiprocessing import Process, Queue
from more_itertools import chunked
from threading import Thread, Event

np.set_printoptions(precision=6, suppress=True)


class SerialProtocol(serial.threaded.Protocol):
    """Protocol class for handling serial communication using serial.threaded"""

    def __init__(self, serial_server):
        self.serial_server = serial_server
        self.buffer = bytearray()

    def connection_made(self, transport):
        """Called when connection is established"""
        self.transport = transport
        print("Serial connection established")

    def data_received(self, data):
        """Called when data is received from serial port"""
        try:
            self.buffer.extend(data)
            self.serial_server.byteBuffer.put(data)

            # Process complete packets
            if len(self.buffer) >= MIN_PACKET_SIZE:
                self.serial_server.parser.parse(self.buffer)

        except Exception as e:
            print(f"[data_received] : Exception: {e}")

    def connection_lost(self, exc):
        """Called when connection is lost"""
        if exc:
            print(f"Serial connection lost: {exc}")
        else:
            print("Serial connection closed")
        self.serial_server.on_connection_lost()


class serialServer:
    def __init__(self, pipe):
        self.pipe = pipe
        self.running: bool = False
        self.portStr: str = ""
        self.filePath: str = ""
        self.sequenceList = []
        self.byteBuffer = Queue()
        self.startTimeStr = time.strftime("%Y-%m-%d-%H-%M-%S")
        self.parser = Parser(callback=lambda frame: self.handle_frame(frame))
        self.protocol = None
        self.serial_worker = None
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.path = f"logs/{self.startTimeStr}.bin"

    @property
    def connected(self) -> bool:
        try:
            return self.port.is_open and self.serial_worker is not None
        except Exception as e:
            print(f"Error in connected property: {e}")
            return False

    def connect(self):
        if self.connected:  # Only disconnect if we're actually connected
            self.disconnect()
        if not self.portStr:
            print("[connect] : No Port Selected")
            return False
        try:
            self.port.open()
            # Start the threaded serial worker
            self.serial_worker = serial.threaded.ReaderThread(self.port, lambda: SerialProtocol(self))
            print(type(self.serial_worker))
            self.serial_worker.start()
            self.transport, self.protocol = self.serial_worker.connect()
            return True
        except Exception as e:
            print(f"[connect] : Error opening port: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            print(f"[disconnect] : Not connected | {self.port.is_open}")
            return True
        try:
            if self.protocol:
                self.protocol.disconnect_from_protocol()
                print(f"[disconnect] : Protocol disconnected| {self.port.is_open}")
            # else:
            # Fallback to direct disconnection
            # if self.serial_worker:
            #     self.serial_worker.close()
            #     self.serial_worker = None
            #     self.protocol = None
            # if self.port.is_open:
            #     self.port.close()
        except Exception as e:
            print(f"[disconnect] : Error closing port: {e} | {self.port.is_open}")
            return False
        print(f"[disconnect] : Successfully disconnected | {self.port.is_open}")
        return True

    def on_connection_lost(self):
        """Called by protocol when connection is lost"""
        self.serial_worker = None
        self.protocol = None
        print("Connection lost, resetting protocol and worker")

    def sendData(self, data: bytes, sequence: int):
        if not self.connected or not data:
            print(f"[sendData] Aborted: connected={self.connected}, data_length={len(data) if data else 0}")
            return False
        try:
            if self.protocol and self.protocol.transport:
                byteSent = 0
                for chunk in chunked(data, 512):
                    chunk_bytes = bytes(chunk)
                    self.protocol.transport.write(chunk_bytes)
                    byteSent += len(chunk_bytes)
                if byteSent == len(data):
                    self.sequenceList.append(sequence)
                    return True
        except Exception as e:
            print(f"[sendData] : Error in sendData: {e}")
            return False

    def SerialRequestSender(self):
        while self.running:
            try:
                request = self.pipe.recv()
            except Exception as e:
                print(f"[SerialRequestSender] : Error receiving request: {e}")
                continue

            match request["event"]:

                case "PORTSELECT":
                    self.portStr, self.port.port = request["port"], request["port"]
                    self.sendResponse(request, True)

                case "CONNECT":
                    self.connect()
                    if self.connected:
                        self.sendData(connect(request["sequence"]), sequence=request["sequence"])
                    else:
                        self.sendResponse(request, False)

                case "DISCONNECT":
                    self.sendData(disconnect(request["sequence"]), sequence=request["sequence"])

                case "ENABLE":
                    self.sendData(enable(request["sequence"]), sequence=request["sequence"])

                case "UPLOAD":
                    self.filePath = request["filePath"]
                    data_array = np.arange(request["sequence"] * 6).reshape((request["sequence"], 6)).astype(np.float32) + 1
                    self.sendData(upload(request["sequence"], data_array), sequence=request["sequence"])

                case "PLAY":
                    self.sendData(play(request["sequence"]), sequence=request["sequence"])

                case "PAUSE":
                    self.sendData(pause(request["sequence"]), sequence=request["sequence"])

                case "STOP":
                    self.sendData(stop(request["sequence"]), sequence=request["sequence"])

                case "DISABLE":
                    self.sendData(disable(request["sequence"]), sequence=request["sequence"])

                case "RESET":
                    self.sendData(reset(request["sequence"]), sequence=request["sequence"])

                case "QUIT":
                    if self.connected:
                        self.sendData(quit(request["sequence"]), sequence=request["sequence"])
                    else:
                        self.sendResponse(request, True)
                        self.running = False
                    break

                case _:
                    print(f"[SerialRequestSender] : Unknown event: {request['event']}")

    def sendResponse(self, response, success=False):
        response["status"] = success
        try:
            self.pipe.send(response)
        except Exception as e:
            print(f"[sendResponse] : Error sending response: {e}")

    def handle_frame(self, frames):
        for frame in frames:
            if frame["msg_id"] == "ACK" or frame["msg_id"] == "NAK":
                response = {
                    "event": frame["payload"],
                    "sequence": frame["sequence"],
                    "status": True if frame["msg_id"] == "ACK" else False,
                }
                if response["sequence"] in self.sequenceList:
                    self.sendResponse(response, True)
                    self.sequenceList.remove(response["sequence"])
                if response["event"] == "RESET" or response["event"] == "DISCONNECT":
                    print(f"[handle_frame | R/D] : {response['event']}")
                    self.disconnect()
                if response["event"] == "QUIT":
                    self.stop()
            else:
                print(f"Unhandled frame: {frame}")

    def run(self):
        try:
            print("Serial server started.")
            self.running = True
            self.rsT = Thread(target=self.SerialRequestSender, name="SerialRequestSender", daemon=True)
            self._writer = Process(target=file_writer, args=(self.byteBuffer, self.path))
            self._writer.start()
            self.rsT.start()
            self.rsT.join()
            self.stop()
            print("Serial server stopped.")
        except Exception as e:
            print(f"[run] : Exception in serial server run: {e}")
            self.stop()
        finally:
            pass

    def foo(self):
        pass

    def stop(self):
        self.running = False
        if self.connected:
            self.disconnect()
        if self.rsT.is_alive():
            self.rsT.join()
        self.pipe.close()
        self.byteBuffer.put(None)  # to stop writer
        self._writer.join()


def file_writer(q: Queue, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        for chunk in iter(q.get, None):  # sentinel-driven loop
            file.write(chunk)


if __name__ == "__main__":
    pass
