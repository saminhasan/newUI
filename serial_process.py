import os
import time
import serial
from parser import Parser
from Hexlink.commands import *
from multiprocessing import Process, Queue
from more_itertools import chunked
from threading import Thread, Event

np.set_printoptions(precision=6, suppress=True)


class serialServer:
    def __init__(self, pipe):
        self.pipe = pipe
        self.running: bool = True
        self.port: serial.Serial = serial.Serial(port=None, timeout=None)
        self.portStr: str = ""
        self.filePath: str = ""
        self.byteBuffer = Queue()
        self.sequenceList = []
        self.startTimeStr = time.strftime("%Y-%m-%d-%H-%M-%S")
        self.path = f"logs/{self.startTimeStr}.bin"

    @property
    def connected(self) -> bool:
        try:
            return self.port.is_open
        except Exception as e:
            print(f"Error in connected property: {e}")
            return False

    def connect(self):
        self.disconnect()
        if not self.portStr:
            print("[connect] : No Port Selected")
            return False
        try:
            self.port.open()
            if not self.listen.is_set():  # start listening
                self.listen.set()
            return True
        except Exception as e:
            print(f"[connect] : Error opening port: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            return True
        if self.listen.is_set():
            self.listen.clear()
        try:
            self.port.close()
        except Exception as e:
            print(f"[disconnect] : Error closing port: {e}")
            return False
        return True

    def sendData(self, data: bytes, sequence: int):
        if not self.connected or not data:
            print(f"[sendData] Aborted: connected={self.connected}, data_length={len(data) if data else 0}")
            return False
        try:
            byteSent = 0
            for chunk in chunked(data, 512):
                byteSent += self.port.write(bytes(chunk))
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

            match request["event"]:
                case "PORTSELECT":
                    self.portStr, self.port.port = request["port"], request["port"]
                    self.sendResponse(request, True)

                case "CONNECT":
                    self.sendResponse(request, self.connect())
                    self.sendData(connect(request["sequence"]), sequence=request["sequence"])

                case "DISCONNECT":
                    self.sendData(disconnect(request["sequence"]), sequence=request["sequence"])
                    self.sendResponse(request, self.disconnect())

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
                    self.sendResponse(request, self.disconnect())

                case "QUIT":
                    if self.connected:
                        self.sendData(quit(request["sequence"]), sequence=request["sequence"])
                    else:
                        self.sendResponse(request, True)
                        self.foo()
                    return

    def sendResponse(self, response, success):
        response["status"] = success
        try:
            self.pipe.send(response)
        except Exception as e:
            print(f"[sendResponse] : Error sending response: {e}")

    def SerialListener(self):
        while self.running:
            self.listen.wait()
            byteBuffer = bytearray()
            while self.running and self.listen.is_set():
                try:
                    if rawBytes := self.port.read(min(self.port.in_waiting, 18)):
                        byteBuffer.extend(rawBytes)
                        self.byteBuffer.put(rawBytes)
                        # print("In Buffer:", " ".join(f"0x{b:02x}" for b in byteBuffer))
                except Exception as e:
                    self.disconnect()
                    self.listen.clear()
                    print(f"[SerialListener] : Exception: {e}")
                    break
                if len(byteBuffer) >= MIN_PACKET_SIZE:
                    self.parser.parse(byteBuffer)

    def handle_frame(self, frames):
        for frame in frames:
            # print(f"handle_frame={frame}")
            if frame.get("msg_id") == "ACK" or frame.get("msg_id") == "NAK":
                event = {
                    "event": frame.get("payload"),
                    "sequence": frame["sequence"],
                    "status": True if frame["msg_id"] == "ACK" else False,
                }
                if frame.get("msg_id") == "NAK":
                    print(f"Error in response: {event}")
                if event["sequence"] in self.sequenceList:
                    self.sendResponse(event, True)
                    self.sequenceList.remove(event["sequence"])
                if event["event"] == "QUIT":
                    self.foo()
            else:
                print(f"Unhandled frame: {frame}")

    def run(self):
        try:
            print("Serial server started.")
            self.parser = Parser(callback=lambda frame: self.handle_frame(frame))
            self.listen = Event()
            self.rsT = Thread(target=self.SerialRequestSender, name="SerialRequestSender", daemon=True)
            self.slT = Thread(target=self.SerialListener, name="SerialListener", daemon=True)
            self._writer = Process(target=file_writer, args=(self.byteBuffer, self.path))
            self._writer.start()
            self.rsT.start()
            self.slT.start()
            self.rsT.join()
            self.slT.join()
            self.stop()
            print("Serial server stopped.")
        except Exception as e:
            print(f"[run] : Exception in serial server run: {e}")
            self.stop()
        finally:
            pass

    def foo(self):
        self.running = False
        self.listen.set()
        self.listen.clear()

    def stop(self):
        if self.connected:
            self.disconnect()
        if self.rsT.is_alive():
            self.rsT.join()
        if self.slT.is_alive():
            self.slT.join()
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
