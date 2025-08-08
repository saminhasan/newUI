import serial
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
        self.sequenceList = []

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
            # self.sequence += 1
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
            try:
                request = self.pipe.recv()
                self.sequenceList.append(request["sequence"])
            except Exception as e:
                print(f"Error receiving request: {e} | SerialRequestSender")
                self.sendData(stop(self.sequenceList[-1]))
                self.running = False
                return

            match request["event"]:
                case "PORTSELECT":
                    self.portStr, self.port.port = request["port"], request["port"]
                    self.sendResponse(request, True)

                case "CONNECT":
                    self.sendResponse(request, self.connect())

                case "DISCONNECT":
                    self.sendResponse(request, self.disconnect())

                case "ENABLE":
                    self.sendData(enable(request["sequence"]))

                case "UPLOAD":
                    self.filePath = request["filePath"]
                    data_array = np.arange(request["sequence"] * 6).reshape((request["sequence"], 6)).astype(np.float32) + 1
                    self.sendData(upload(request["sequence"], data_array))

                case "PLAY":
                    self.sendData(play(request["sequence"]))

                case "PAUSE":
                    self.sendData(pause(request["sequence"]))

                case "STOP":
                    self.sendData(stop(request["sequence"]))

                case "DISABLE":
                    self.sendData(disable(request["sequence"]))

                case "RESET":
                    self.sendData(reset(request["sequence"]))
                    self.sendResponse(request, self.disconnect())
                case "QUIT":  # Handle additional quit logic from here such as sending stop signal to teensy
                    self.running = False
                    self.listen.set()
                    self.listen.clear()
                    self.sendResponse(request, True)
                    return

    def sendResponse(self, response, success):
        response["status"] = "ACK" if success else "NAK"
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
                    # if not (self.connected and (rawBytes := self.port.read(max(self.port.in_waiting, PACKET_OVERHEAD + 1)))):
                    if not (self.connected and (rawBytes := self.port.read(1))):
                        continue
                    byteBuffer.extend(rawBytes)
                    # print(f"In Buffer:", end=" ")
                    # for b in byteBuffer:
                    #     print(f"0x{b:02x}", end=" ")
                    # print()
                    frames = self.parser.parse(byteBuffer)

                except serial.SerialException as e:
                    self.disconnect()
                    self.listen.clear()
                    print(f"Serial error: {e}")

                except Exception as e:
                    print(f"Exception: {e}")

    def handle_frame(self, frame):
        print(f"handle_frame:={frame}")
        if frame.get("msg_name") == "ACK" or frame.get("msg_name") == "NAK":

            # print(frame.get("payload", None), type(frame.get("payload", None)), len(frame.get("payload", None)))
            # print(frame.get("payload", None)[1], type(frame.get("payload", None)[1]))
            # print(msgIDs[bytes([frame.get("payload", None)[-1]])])
            # print(frame.get("sequence", None))
            # print(frame.get("msg_name"))
            # print(f"{True if frame.get("msg_name") == "ACK" else False}")
            event = {
                "event": msgIDs[bytes([frame.get("payload", None)[-1]])],
                "sequence": frame.get("sequence", None),
                "status": True if frame.get("msg_name") == "ACK" else False,
            }
            if event["sequence"] in self.sequenceList:
                self.sendResponse(event, True)
                self.sequenceList.remove(event["sequence"])

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
