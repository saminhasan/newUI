import tkinter as tk
import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox
from multiprocessing import Process, Pipe, Queue
from threading import Thread, Event
from appModel import FSM
import time
from UI.custom_combobox import CustomComboBox
from serial_process import serialServer, portList
from queue import Empty

WIDTH: int = 960
HEIGHT: int = 480
MAX_LINES = 1000

usb_icon = Image.open("Icons/usb.png")
usb_off_icon = Image.open("Icons/usb_off.png")
play_icon = Image.open("Icons/play.png")
pause_icon = Image.open("Icons/pause.png")
stop_icon = Image.open("Icons/stop.png")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.seq: int = 0
        self.running: bool = True
        self.response: dict = {}
        self.parentConnection, self.childConnection = Pipe()
        self.fsm: FSM = FSM()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
        self.bind("<<ReceivedResponse>>", self.responseHandler)
        self.resLT: Thread = Thread(target=self.responseListener, daemon=True, name="ResponseListenerThread")

    def create_widgets(self):
        self.title("Hexapod Controller")
        # self.geometry(f"{WIDTH}x{HEIGHT}")
        self.resizable(True, True)
        # self.minsize(WIDTH, HEIGHT)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.controlPanel: ctk.CTkFrame = ctk.CTkFrame(self, corner_radius=10)
        self.controlPanel.grid(row=0, column=0, sticky="nsew")
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

        # Connection buttons frame
        self.connectionFrame = ctk.CTkFrame(self.controlPanel)
        self.connectionFrame.grid(row=0, column=4, columnspan=2, sticky="we", padx=(5, 10), pady=(10, 10))
        self.connectionFrame.grid_columnconfigure(0, weight=1)
        self.connectionFrame.grid_columnconfigure(1, weight=1)

        self.connectBtn = ctk.CTkButton(
            self.connectionFrame,
            text="",
            command=lambda: self.requestHandler("connect"),
            image=ctk.CTkImage(light_image=usb_icon, dark_image=usb_icon),
            hover_color="green4",
            fg_color="darkgreen",
        )
        self.connectBtn.grid(row=0, column=0, sticky="nsew", padx=(5, 2.5), pady=5)
        self.disconnectBtn = ctk.CTkButton(
            self.connectionFrame,
            text="",
            command=lambda: self.requestHandler("disconnect"),
            image=ctk.CTkImage(light_image=usb_off_icon, dark_image=usb_off_icon),
        )
        self.disconnectBtn.grid(row=0, column=1, sticky="nsew", padx=(2.5, 5), pady=5)

        self.controlPanelWidgets["connect"] = self.connectBtn
        self.controlPanelWidgets["disconnect"] = self.disconnectBtn
        self.enableBtn = ctk.CTkButton(
            self.controlPanel,
            text="ENABLE",
            command=lambda: self.requestHandler("enable"),
            # fg_color="transparent",
        )
        self.enableBtn.grid(row=1, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["enable"] = self.enableBtn
        self.uploadBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="UPLOAD", command=lambda: self.fileHandler("upload")
        )
        self.uploadBtn.grid(row=3, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["upload"] = self.uploadBtn

        # Playback buttons frame
        self.playbackFrame = ctk.CTkFrame(self.controlPanel)
        self.playbackFrame.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.playbackFrame.grid_columnconfigure(0, weight=1)
        self.playbackFrame.grid_columnconfigure(1, weight=1)
        self.playbackFrame.grid_columnconfigure(2, weight=1)
        self.playbackFrame.grid_rowconfigure(0, weight=1)

        self.playBtn = ctk.CTkButton(self.playbackFrame, text="►", command=lambda: self.requestHandler("play"))
        self.playBtn.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.pauseBtn = ctk.CTkButton(self.playbackFrame, text="||", command=lambda: self.requestHandler("pause"))
        self.pauseBtn.grid(row=0, column=1, sticky="nsew", padx=(5, 5), pady=10)
        self.stopBtn = ctk.CTkButton(self.playbackFrame, text="■", command=lambda: self.requestHandler("stop"))
        self.stopBtn.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

        self.controlPanelWidgets["play"] = self.playBtn
        self.controlPanelWidgets["pause"] = self.pauseBtn
        self.controlPanelWidgets["stop"] = self.stopBtn
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
        if current_state not in ["DISCONNECTED", "IDLE", "ERROR"]:
            self.connectBtn.configure(fg_color="chartreuse")
        else:
            self.connectBtn.configure(fg_color="darkgreen")

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
        # file_path = filedialog.askopenfilename(title="Select File", filetypes=[("All Files", "*.*")])
        # if file_path:  # call checking function here or maybe even plot the file
        #     self.requestHandler(event_name, filePath=file_path)
        # else:
        #     messagebox.showwarning("No File Selected", "Please select a file to upload.")
        #     self.fileHandler()
        self.requestHandler(event_name, filePath="file_path_placeholder")

    def requestHandler(self, event_name, **kwargs):
        eventDict = {"event": event_name, "seq": self.seq}
        if kwargs:
            eventDict.update(kwargs)
        self.parentConnection.send(eventDict)
        self.seq += 1
        self.childConnection.send(eventDict)

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

    def run(self):
        self.resLT.start()
        self.mainloop()

    def on_closing(self):
        self.running = False
        self.requestHandler("quit")
        if self.resLT.is_alive():
            self.resLT.join()
        self.parentConnection.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.run()
    print("Done.")
