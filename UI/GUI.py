import customtkinter as ctk
from tkinter import filedialog, messagebox
from multiprocessing import Process, Pipe, Queue
from threading import Thread, Event
from model import FSM
import time
from UI.custom_tabview import CustomTabview
from UI.custom_combobox import CustomComboBox
from serial_process import serialServer
from queue import Empty
from serial.tools import list_ports, list_ports_common

WIDTH: int = 960
HEIGHT: int = 480
MAX_LINES = 1000


def portList() -> list[list_ports_common.ListPortInfo]:
    return list_ports.comports()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.seq: int = 0
        self.running: bool = True
        self.response: dict = {}
        self.recvQ: Queue = Queue()
        self.parentConnection, self.childConnection = Pipe()
        self.fsm: FSM = FSM()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
        self.comServer: serialServer = serialServer(self.childConnection)
        self.comProcess: Process = Process(target=self.comServer.run, name="SerialServerProcess")
        self.bind("<<ReceivedResponse>>", self.responseHandler)
        self.resLT: Thread = Thread(target=self.responseListener, daemon=True, name="ResponseListenerThread")
        self.after(0, self.dataHandler)

    def create_widgets(self):
        self.title("UI")
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(True, True)
        self.minsize(WIDTH, HEIGHT)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=0)
        self.tabL: CustomTabview = CustomTabview(self)
        self.tabL.grid(row=1, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.logTab = self.tabL.add("  Log  ")
        self.logTab.grid_rowconfigure(0, weight=1)
        self.logTab.grid_columnconfigure(0, weight=1)
        self.logTerminal: ctk.CTkTextbox = ctk.CTkTextbox(self.logTab)
        self.logTerminal.tag_config("info", foreground="green")
        self.logTerminal.tag_config("warning", foreground="orange")
        self.logTerminal.tag_config("error", foreground="red")
        self.logTerminal.tag_config("debug", foreground="gray")
        self.logTerminal.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.logTerminal.configure(state="disabled")

        self.stateTab: CustomTabview = self.tabL.add("  State  ")
        self.dataTab: CustomTabview = self.tabL.add("  Data  ")

        self.tabR: CustomTabview = CustomTabview(self)
        self.tabR.grid(row=1, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanel: ctk.CTkFrame = self.tabR.add("Control Panel")
        self.controlPanelWidgets: dict = {}
        for col in range(6):
            self.controlPanel.grid_columnconfigure(col, weight=1)
        for row in range(1, 10):
            self.controlPanel.grid_rowconfigure(row, weight=1)
        self.portSelect: CustomComboBox = CustomComboBox(
            self.controlPanel,
            values=[""],
            dropdown_pressed_callback=self.dropdown_callback,
            width=280,
            command=lambda event: self.requestHandler("portSelect", port=event),
        )
        self.portSelect.grid(row=0, column=0, columnspan=3, sticky="we", padx=(10, 5), pady=(10, 10))
        self.controlPanelWidgets["portSelect"] = self.portSelect
        self.connectionSegment = ctk.CTkSegmentedButton(self.controlPanel, values=["C", "D"], dynamic_resizing=False)
        self.connectionSegment.grid(row=0, column=4, columnspan=4, sticky="we", padx=(5, 10), pady=(10, 10))
        self.controlPanelWidgets["connect"] = self.connectionSegment._buttons_dict["C"]
        self.controlPanelWidgets["disconnect"] = self.connectionSegment._buttons_dict["D"]
        self.controlPanelWidgets["connect"].configure(command=lambda: self.requestHandler("connect"))
        self.controlPanelWidgets["disconnect"].configure(command=lambda: self.requestHandler("disconnect"))
        self.enableBtn = ctk.CTkButton(self.controlPanel, text="ENABLE", command=lambda: self.requestHandler("enable"))
        self.enableBtn.grid(row=1, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["enable"] = self.enableBtn
        self.uploadBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="UPLOAD", command=lambda: self.fileHandler("upload")
        )
        self.uploadBtn.grid(row=3, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["upload"] = self.uploadBtn
        self.playbackSegment: ctk.CTkSegmentedButton = ctk.CTkSegmentedButton(
            self.controlPanel, values=["►", "||", "■"], state="normal", dynamic_resizing=False
        )
        self.playbackSegment.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["play"] = self.playbackSegment._buttons_dict["►"]
        self.controlPanelWidgets["pause"] = self.playbackSegment._buttons_dict["||"]
        self.controlPanelWidgets["stop"] = self.playbackSegment._buttons_dict["■"]
        self.controlPanelWidgets["play"].configure(command=lambda: self.requestHandler("play"))
        self.controlPanelWidgets["pause"].configure(command=lambda: self.requestHandler("pause"))
        self.controlPanelWidgets["stop"].configure(command=lambda: self.requestHandler("stop"))
        self.disableBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="EStop", command=lambda: self.requestHandler("disable"), fg_color="red4", hover_color="red2"
        )
        self.disableBtn.grid(row=7, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["disable"] = self.disableBtn
        self.resetBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="RESET", command=lambda: self.requestHandler("reset")
        )
        self.resetBtn.grid(row=9, column=0, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["reset"] = self.resetBtn

    def configure_widgets(self, to_enable=None, current_state=None):
        enabled_widgets: set = set(to_enable or ())
        for key, w in self.controlPanelWidgets.items():
            current = w.cget("state")
            if key not in enabled_widgets and current != "disabled":
                w.configure(state="disabled")
        for key in enabled_widgets:
            w = self.controlPanelWidgets.get(key)
            if w is not None:
                current = w.cget("state")
                if current != "normal":
                    w.configure(state="normal")

    def dropdown_callback(self):
        self.portsDict = {
            port.device: port
            for port in portList()
            if ((port.pid == 1155 or port.pid == 1163 or port.pid == 1164) and port.vid == 5824)
        }
        if self.portsDict:
            self.portSelect.configure(values=list(self.portsDict.keys()))
        else:
            self.portSelect.configure(values=[])

    def fileHandler(self, event_name="upload"):
        file_path = filedialog.askopenfilename(title="Select File", filetypes=[("All Files", "*.*")])
        if file_path:  # call checking function here or maybe even plot the file
            self.requestHandler(event_name, filePath=file_path)
        else:
            messagebox.showwarning("No File Selected", "Please select a file to upload.")
            self.fileHandler()

    def requestHandler(self, event_name, **kwargs):
        eventDict = {"event": event_name, "seq": self.seq}
        if kwargs:
            eventDict.update(kwargs)
        self.parentConnection.send(eventDict)
        self.seq += 1

    def responseListener(self):
        while self.running:
            self.response = self.parentConnection.recv()
            if self.response.get("event", None) == "quit":
                break
            else:
                self.after(0, lambda: self.event_generate("<<ReceivedResponse>>", when="tail"))

    def responseHandler(self, VirtualEvent=None):
        event = self.response.get("event", None)
        if event is not None:
            if event in self.fsm.available_transitions():
                self.fsm.trigger(event)
                if event != "quit":
                    self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
            else:
                raise (f"Event {event} not in: {self.fsm.available_transitions()}")
        self.response = {}

    def dataHandler(self, VirtualEvent=None):  # add tags for info warning error and stuff
        data = []
        while not self.recvQ.empty():
            try:
                data.append(self.recvQ.get_nowait())
            except Empty:
                pass
        if self.running:
            if data:
                self.updateLog(data)
            self.after(10, self.dataHandler)

    def updateLog(self, data):
        # print(data)
        data_str = "".join(f"{item['tag']}:{item['entry']}" for item in data)
        self.logTerminal.configure(state="normal")
        self.logTerminal.insert("end", data_str)

        num_lines = int(self.logTerminal.index("end-1c").split(".")[0])
        if num_lines > MAX_LINES:
            self.logTerminal.delete("1.0", f"{num_lines - MAX_LINES}.0")
        self.logTerminal.configure(state="disabled")

        _, last = self.logTerminal.yview()  # Auto Scroll to the end of the log terminal
        if last > 0.8:
            self.logTerminal.yview("end")

    def run(self):
        self.comProcess.start()
        self.resLT.start()
        self.mainloop()

    def on_closing(self):
        self.running = False
        self.requestHandler("quit")
        if self.resLT.is_alive():
            self.resLT.join()
        self.dataHandler()
        self.comProcess.join()
        self.parentConnection.close()
        self.recvQ.close()
        self.recvQ.join_thread()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.run()
    print("Done.")
