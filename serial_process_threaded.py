import os
import time
import serial
import serial.threaded
import numpy as np
from parser import Parser, decodePayload
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
            print(f"[data_received] : Exception: {e} | Data : {data}")

    def connection_lost(self, exc):
        """Called when connection is lost"""
        if exc:
            print(f"Protocol : [connection_lost] : Error : Serial connection lost: {exc}")
        else:
            print("Protocol : [connection_lost] : Serial connection closed cleanly")
        self.serial_server.on_connection_lost(popup=True if exc else False)

    def disconnect_from_protocol(self):
        """Disconnect from within the protocol thread"""
        if self.transport:
            self.transport.close()  # This will trigger connection_lost()


class serialServer:
    def __init__(self, pipe):
        self.pipe = pipe
        self.running: bool = False
        self.portStr: str = ""
        self.filePath: str = ""
        self.sequenceList = []
        self.byteBuffer = Queue()
        self.startTimeStr = time.strftime("%Y-%m-%d-%H-%M-%S")
        self.parser = None  # Will be initialized in run()
        self.protocol = None
        self.serial_worker = None
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.path = f"logs/{self.startTimeStr}.bin"

    @property
    def connected(self) -> bool:
        try:
            return self.port.is_open and self.serial_worker is not None
        except Exception as e:
            print(f"[connected] : Error - {e}")
            return False

    def connect(self):
        if not self.portStr:
            print("[connect] : No Port Selected")  # should not happen, but still here to handle gracefully
            return False

        if self.connected and (self.port.port == self.portStr):  # Only disconnect if we're actually connected
            return True

        try:
            self.port.open()
            self.serial_worker = serial.threaded.ReaderThread(self.port, lambda: SerialProtocol(self))
            self.serial_worker.start()
            self.transport, self.protocol = self.serial_worker.connect()
            return True
        except Exception as e:
            print(f"[connect] : Error opening port - {e}")
            return False

    def disconnect(self):
        if not self.connected:
            return True
        try:
            self.transport.alive = False  # tell loop to stop
            if hasattr(self.transport.serial, "cancel_read"):
                self.transport.serial.cancel_read()
            if self.port.is_open:
                self.port.close()
        except Exception as e:
            print(f"[disconnect] : Error closing port - {e} | {self.port.is_open}")
            return False
        return True

    def on_connection_lost(self, popup: bool = False):
        """Called by protocol when connection is lost"""
        self.serial_worker = None
        self.protocol = None
        if popup:
            self.sendResponse({"event": "DISCONNECT", "sequence": -1, "popup": "Connection lost"}, True)
        try:
            if self.port.is_open:
                self.port.close()
        except Exception as e:
            print(f"[on_connection_lost] : Error closing port - {e} | {self.port.is_open}")

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
            print(f"[sendData] : Error in sendData - {e}")
            return False

    def SerialRequestSender(self):
        while self.running:
            try:
                request = self.pipe.recv()
            except Exception as e:
                print(f"[SerialRequestSender] : Error receiving request - {e}")
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
                    self.filePath = request["filePath"]  # get data array only as a dict
                    data_array = np.arange(request["sequence"] * 6).reshape((request["sequence"], 6)).astype(np.float32) + 1
                    print(f"[SerialRequestSender] : Data Array: {data_array[-1]}")
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
                    break

                case _:
                    print(f"[SerialRequestSender] : Unknown event - {request['event']}")

    def sendResponse(self, response, success=False):
        response["status"] = success
        try:
            self.pipe.send(response)
        except Exception as e:
            print(f"[sendResponse] : Error sending response - {e}")

    def handle_frame(self, frames):
        # print(f"[handle_frame] : {len(frames)} Frames Received: {frames}")
        while frames:
            frame = frames.popleft()
            match frame["msg_id"]:
                case "ACK" | "NAK":
                    if frame["sequence"] in self.sequenceList:
                        self.sendResponse({"event": frame["payload"], "sequence": frame["sequence"]}, frame["msg_id"] == "ACK")
                        self.sequenceList.remove(frame["sequence"])
                    if frame["payload"] == "RESET" or frame["payload"] == "DISCONNECT":
                        self.disconnect()
                    if frame["msg_id"] == "QUIT":
                        self.stop()
                case "INFO":
                    print(f"[INFO] : {frame['payload']}")
                case _:
                    print(f"[(un)handle_frame] : msg_id={frame['msg_id']}, payload={frame['payload']}")

    def run(self):
        try:
            print("Serial server started.")
            self.parser = Parser(callback=self.handle_frame)  # Initialize parser here instead of __init__
            self.running = True
            self.rsT = Thread(target=self.SerialRequestSender, name="SerialRequestSender", daemon=True)
            self._writer = Process(target=file_writer, args=(self.byteBuffer, self.path))
            self._writer.start()
            self.rsT.start()
            self.rsT.join()
            self.stop()
            print("Serial server stopped.")
        except Exception as e:
            print(f"[run] : Exception in serial server run - {e}")
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
        self.byteBuffer.put(None)  # to stop writer
        self._writer.join()
        self.pipe.close()


def file_writer(q: Queue, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        for chunk in iter(q.get, None):  # sentinel-driven loop
            file.write(chunk)


if __name__ == "__main__":
    pass
