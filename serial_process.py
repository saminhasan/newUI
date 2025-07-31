from multiprocessing import Process, Pipe
from threading import Thread, Event
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo
import time
import serial

def portList() -> list[ListPortInfo]:
    return list_ports.comports()

class serialServer:
    def __init__(self, conn):
        self.conn = conn  # This is the child end of the pipe
        self.running : bool= True
        self.port : serial.Serial | None = None
        self.portStr : str = ""
        self.connected : bool = False
        self.filePath : str = ""

    def connect(self):
        if self.portStr:
            print(f"Opening :  {self.portStr} | Starting serial connection...")
            self.connected = True
            try:
                self.port = serial.Serial(self.portStr,timeout=0)
                if self.port.is_open:
                    return True
            except Exception as e:
                print(f"Error opening serial port: {e}")


    def disconnect(self):
        if self.connected:
            print(f"Closing : {self.portStr} | Stopping serial connection...")
            try:
                if self.port.is_open:
                    self.port.close()
                self.connected = False
                return True
            except Exception as e:
                print(f"Error closing serial port: {e}")

    def sendRequest(self, request):
        status = False
        # print(f"Request : {request}")
        if request['event'] == "portSelect":
            self.portStr = request['port']
            print(f"{self.portStr=}")
        # if request['event'] == "connect":
        #     status = self.connect()
        # if request['event'] == "disconnect":
        #     status = self.disconnect()
        if request['event'] == "upload":
            self.filePath = request['filePath']
            print(f"{self.filePath=}")
        if request['event'] == "quit":
                self.running = False
        response = request
        response['status'] = 'ACK' if status else 'NAK'
        self.conn.send(response)


    def handleResponse(self, response):
        pass

    def run(self):
        print("Serial server started.")
        try:
            while self.running:
                print("LOOPING")
                request = self.conn.recv()
                self.sendRequest(request)
                # else:
                #     time.sleep(0.01)  # Small delay to prevent busy waiting
                # # if self.connected and self.port.is_open:
                # #     pass



        except Exception as e:
            print(f"Error in serialServer: {e}")
        finally:
            self.stop()

    def stop(self):
        if self.connected:
            self.disconnect()
        print("Serial server stopped.")

if __name__ == "__main__":
    parent_conn, child_conn = Pipe()
    ss = serialServer(child_conn)
    ssp = Process(target=ss.run)
    ssp.start()
    parent_conn.send({"event": "test", "data": "Hello, World!"})
    time.sleep(1)  # Allow some time for processing
    if parent_conn.poll():
        response = parent_conn.recv()
        print(f"Received response: {response}")
    parent_conn.send({"event": "quit"})
    ssp.join()
    parent_conn.close()
    child_conn.close()