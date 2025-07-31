import customtkinter as ctk
from tkinter import filedialog, messagebox
from multiprocessing import Process, Pipe, Queue
from threading import Thread
from appModel import FSM
import time
from UI.custom_tabview import CustomTabview
from UI.custom_combobox import CustomComboBox
from serial_process import serialServer, portList

WIDTH: int = 640
HEIGHT: int = 480


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.seq: int = 0
        self.running: bool = True
        self.fsm = FSM()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
        self.parent_conn, self.child_conn = Pipe()
        self.recvQ = Queue()
        self.comServer = serialServer(self.child_conn, self.recvQ)
        self.comProcess = Process(target=self.comServer.run, name="SerialServerProcess")
        self.bind("<<ReceivedResponse>>", self.responseHandler)
        self.resT = Thread(target=self.rCB, daemon=True)

        self.bind("<<ReceivedData>>", self.dataHandler)
        self.lisT = Thread(target=self.listener, daemon=True)
        self.response: dict = {}
        self.data = []

    def create_widgets(self):
        self.title("UI")
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(True, True)
        self.minsize(WIDTH, HEIGHT)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=0)
        self.tabL = CustomTabview(self)
        self.tabL.grid(row=1, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.logTab = self.tabL.add("  Log  ")
        self.logTab.grid_rowconfigure(0, weight=1)
        self.logTab.grid_columnconfigure(0, weight=1)
        self.logTerminal = ctk.CTkTextbox(self.logTab)
        self.logTerminal.tag_config("info", foreground="green")
        self.logTerminal.tag_config("warning", foreground="orange")
        self.logTerminal.tag_config("error", foreground="red")
        self.logTerminal.tag_config("debug", foreground="gray")
        self.logTerminal.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.logTerminal.configure(state="disabled")
        self.stateTab = self.tabL.add("  State  ")
        self.dataTab = self.tabL.add("  Data  ")

        self.tabR = CustomTabview(self)
        self.tabR.grid(row=1, column=1, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanel = self.tabR.add("Control Panel")
        self.controlPanelWidgets = {}
        for col in range(6):
            self.controlPanel.grid_columnconfigure(col, weight=1)
        for row in range(1, 10):
            self.controlPanel.grid_rowconfigure(row, weight=1)
        self.portSelect = CustomComboBox(
            self.controlPanel,
            values=[""],
            dropdown_pressed_callback=self.dropdown_callback,
            width=280,
            command=lambda event: self.eventHandler("portSelect", port=event),
        )
        self.portSelect.grid(row=0, column=0, columnspan=3, sticky="we", padx=(10, 5), pady=(10, 10))
        self.controlPanelWidgets["portSelect"] = self.portSelect
        self.connectionSegment = ctk.CTkSegmentedButton(self.controlPanel, values=["C", "D"], dynamic_resizing=False)
        self.connectionSegment.grid(row=0, column=4, columnspan=4, sticky="we", padx=(5, 10), pady=(10, 10))
        self.controlPanelWidgets["connect"] = self.connectionSegment._buttons_dict["C"]
        self.controlPanelWidgets["disconnect"] = self.connectionSegment._buttons_dict["D"]
        self.controlPanelWidgets["connect"].configure(command=lambda: self.eventHandler("connect"))
        self.controlPanelWidgets["disconnect"].configure(command=lambda: self.eventHandler("disconnect"))
        self.enableBtn = ctk.CTkButton(self.controlPanel, text="ENABLE", command=lambda: self.eventHandler("enable"))
        self.enableBtn.grid(row=1, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["enable"] = self.enableBtn
        self.uploadBtn = ctk.CTkButton(self.controlPanel, text="UPLOAD", command=lambda: self.fileHandler("upload"))
        self.uploadBtn.grid(row=3, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["upload"] = self.uploadBtn
        self.playbackSegment = ctk.CTkSegmentedButton(
            self.controlPanel, values=["▶︎", "|| ", " ■"], font=("Cascadia Code", 24), state="normal", dynamic_resizing=False
        )
        self.playbackSegment.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["play"] = self.playbackSegment._buttons_dict["▶︎"]
        self.controlPanelWidgets["pause"] = self.playbackSegment._buttons_dict["|| "]
        self.controlPanelWidgets["stop"] = self.playbackSegment._buttons_dict[" ■"]
        self.controlPanelWidgets["play"].configure(command=lambda: self.eventHandler("play"))
        self.controlPanelWidgets["pause"].configure(command=lambda: self.eventHandler("pause"))
        self.controlPanelWidgets["stop"].configure(command=lambda: self.eventHandler("stop"))
        self.disableBtn = ctk.CTkButton(
            self.controlPanel, text="EStop", command=lambda: self.eventHandler("disable"), fg_color="red4", hover_color="red2"
        )
        self.disableBtn.grid(row=7, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["disable"] = self.disableBtn
        self.resetBtn = ctk.CTkButton(self.controlPanel, text="RESET", command=lambda: self.eventHandler("reset"))
        self.resetBtn.grid(row=9, column=0, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["reset"] = self.resetBtn

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
            self.eventHandler(event_name, filePath=file_path)
        else:
            messagebox.showwarning("No File Selected", "Please select a file to upload.")
            self.fileHandler()

    def rCB(self):
        print("Response handler started.")
        while self.running:
            self.response = self.parent_conn.recv()
            if self.response.get("event", None) == "quit":
                break
            else:
                self.after(0, lambda: self.event_generate("<<ReceivedResponse>>", when="tail"))
        print("Response handler Stopped.")

    def listener(self):  # fix this for quit checking, also maybe reokace kist with nother q or dq
        print("Data handler started.")
        while self.running:
            self.data = self.recvQ.get()
            # print(f"{self.data=}")
            if bool([print(d) for d in self.data if d.get("event") == "quit"]):
                print("Quit event received, stopping data handler.")
                self.recvQ.close()
                break
            else:
                self.after(0, lambda: self.event_generate("<<ReceivedData>>", when="tail"))
        print("Data handler Stopped.")

    def eventHandler(self, event_name, **kwargs):
        eventDict = {"event": event_name, "seq": self.seq}
        if kwargs:
            eventDict.update(kwargs)
        self.parent_conn.send(eventDict)
        self.seq += 1

    def dataHandler(self, VirtualEvent=None):  # add tags for info warning error and stuff
        # print(f"Received data: {self.data}")
        if self.data is None:
            return
        self.logTerminal.configure(state="normal")
        # print(f"Data: {self.data}")
        # assuming self.data is now a list of dicts
        infos = [d.get("INFO", None) for d in self.data if d.get("INFO", None) is not None]

        if infos:
            data_str = "".join(str(x) for x in infos)
            self.logTerminal.insert("end", data_str)
        self.logTerminal.configure(state="disabled")
        _, last = self.logTerminal.yview()
        if last > 0.9:
            self.logTerminal.yview("end")
        self.data = []

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

    def configure_widgets(self, to_enable=None, current_state=None):

        en = set(to_enable or ())
        for key, w in self.controlPanelWidgets.items():
            current = w.cget("state")
            if key not in en and current != "disabled":
                w.configure(state="disabled")
        for key in en:
            w = self.controlPanelWidgets.get(key)
            if w is not None:
                current = w.cget("state")
                if current != "normal":
                    w.configure(state="normal")

    def run(self):
        self.comProcess.start()
        self.resT.start()
        self.lisT.start()
        self.mainloop()

    def on_closing(self):
        self.running = False
        self.eventHandler("quit")
        if self.resT.is_alive():
            self.resT.join()
        if self.lisT.is_alive():
            self.lisT.join()
        self.comProcess.join()
        self.parent_conn.close()
        self.recvQ.close()
        self.recvQ.join_thread()
        self.destroy()


if __name__ == "__main__":
    # # This is required for multiprocessing on Windows
    # import multiprocessing

    # multiprocessing.freeze_support()

    app = App()
    app.run()
    print("Done.")
