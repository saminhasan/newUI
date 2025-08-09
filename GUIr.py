from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
from UI.custom_combobox import CustomComboBox
from serial.tools import list_ports, list_ports_common
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from model import FSM
from threading import Thread
from serial_process import serialServer


WIDTH: int = 800
HEIGHT: int = 480

usb_icon = Image.open("Icons/usb.png")
usb_off_icon = Image.open("Icons/usb_off.png")
play_icon = Image.open("Icons/play.png")
pause_icon = Image.open("Icons/pause.png")
stop_icon = Image.open("Icons/stop.png")


def portList() -> list[list_ports_common.ListPortInfo]:
    return list_ports.comports()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.sequence: int = 0
        self.running: bool = True
        self.response: dict = {}
        self.parentConnection: Connection
        self.childConnection: Connection
        self.parentConnection, self.childConnection = Pipe()
        self.fsm: FSM = FSM()
        self.create_widgets()
        self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
        self.bind("<<ReceivedResponse>>", self.responseHandler)
        self.resLT: Thread = Thread(target=self.responseListener, daemon=True, name="ResponseListenerThread")
        self.comServer: serialServer = serialServer(self.childConnection)
        self.comProcess: Process = Process(target=self.comServer.run, name="SerialServerProcess")

    def create_widgets(self) -> None:
        self.title("Hexapod Controller")
        self.resizable(True, True)
        self.minsize(WIDTH, HEIGHT)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.controlPanel: ctk.CTkFrame = ctk.CTkFrame(self, corner_radius=10)
        self.controlPanel.grid(row=0, column=0, sticky="nsew")
        self.controlPanelWidgets: dict = {}
        for col in range(6):
            self.controlPanel.grid_columnconfigure(col, weight=1)
        for row in range(10):
            self.controlPanel.grid_rowconfigure(row, weight=1)
        self.portSelect: CustomComboBox = CustomComboBox(
            self.controlPanel,
            values=[""],
            dropdown_pressed_callback=self.dropdown_callback,
            width=280,
            state="readonly",
            command=lambda event: self.requestHandler("PORTSELECT", port=event),
        )
        self.portSelect.grid(row=0, column=0, columnspan=3, sticky="we", padx=(10, 5), pady=(10, 10))
        self.controlPanelWidgets["PORTSELECT"] = self.portSelect

        self.connectionFrame = ctk.CTkFrame(self.controlPanel)
        self.connectionFrame.grid(row=0, column=4, columnspan=2, sticky="we", padx=(5, 10), pady=(10, 10))
        self.connectionFrame.grid_columnconfigure(0, weight=1)
        self.connectionFrame.grid_columnconfigure(1, weight=1)

        self.connectBtn = ctk.CTkButton(
            self.connectionFrame,
            text="",
            command=lambda: self.requestHandler("CONNECT"),
            image=ctk.CTkImage(light_image=usb_icon, dark_image=usb_icon),
            hover_color="green4",
            fg_color="transparent",
        )
        self.connectBtn.grid(row=0, column=0, sticky="nsew", padx=(5, 2.5), pady=5)
        self.disconnectBtn = ctk.CTkButton(
            self.connectionFrame,
            text="",
            command=lambda: self.requestHandler("DISCONNECT"),
            image=ctk.CTkImage(light_image=usb_off_icon, dark_image=usb_off_icon),
            hover_color="red",
            fg_color="transparent",
        )
        self.disconnectBtn.grid(row=0, column=1, sticky="nsew", padx=(2.5, 5), pady=5)

        self.controlPanelWidgets["CONNECT"] = self.connectBtn
        self.controlPanelWidgets["DISCONNECT"] = self.disconnectBtn
        self.enableBtn = ctk.CTkButton(
            self.controlPanel,
            text="ENABLE",
            command=lambda: self.requestHandler("ENABLE"),
        )
        self.enableBtn.grid(row=1, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["ENABLE"] = self.enableBtn
        self.uploadBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="UPLOAD", command=lambda: self.fileHandler("UPLOAD")
        )
        self.uploadBtn.grid(row=3, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["UPLOAD"] = self.uploadBtn

        self.playbackFrame = ctk.CTkFrame(self.controlPanel)
        self.playbackFrame.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.playbackFrame.grid_columnconfigure(0, weight=1)
        self.playbackFrame.grid_columnconfigure(1, weight=1)
        self.playbackFrame.grid_columnconfigure(2, weight=1)
        self.playbackFrame.grid_rowconfigure(0, weight=1)

        self.playBtn = ctk.CTkButton(
            self.playbackFrame,
            text="",
            command=lambda: self.requestHandler("PLAY"),
            image=ctk.CTkImage(light_image=play_icon, dark_image=play_icon),
            hover_color="dark green",
            fg_color="transparent",
        )
        self.playBtn.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.pauseBtn = ctk.CTkButton(
            self.playbackFrame,
            text="",
            command=lambda: self.requestHandler("PAUSE"),
            image=ctk.CTkImage(light_image=pause_icon, dark_image=pause_icon),
            hover_color="yellow4",
            fg_color="transparent",
        )
        self.pauseBtn.grid(row=0, column=1, sticky="nsew", padx=(5, 5), pady=10)
        self.stopBtn = ctk.CTkButton(
            self.playbackFrame,
            text="",
            command=lambda: self.requestHandler("STOP"),
            image=ctk.CTkImage(light_image=stop_icon, dark_image=stop_icon),
            hover_color="red4",
            fg_color="transparent",
        )
        self.stopBtn.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

        self.controlPanelWidgets["PLAY"] = self.playBtn
        self.controlPanelWidgets["PAUSE"] = self.pauseBtn
        self.controlPanelWidgets["STOP"] = self.stopBtn
        self.disableBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel,
            text="DISABLE",
            command=lambda: self.requestHandler("DISABLE"),
            fg_color="red4",
            hover_color="red2",
        )
        self.disableBtn.grid(row=7, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["DISABLE"] = self.disableBtn
        self.resetBtn: ctk.CTkButton = ctk.CTkButton(
            self.controlPanel, text="RESET", command=lambda: self.requestHandler("RESET")
        )
        self.resetBtn.grid(row=9, column=0, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.controlPanelWidgets["RESET"] = self.resetBtn
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_widgets(self, to_enable=None, current_state=None) -> None:
        # return
        # enabled_widgets = set(to_enable or ())
        enabled_widgets = to_enable
        for key, w in self.controlPanelWidgets.items():
            target_state = "normal" if key in enabled_widgets else "disabled"
            # if w.cget("state") != target_state:
            w.configure(state=target_state)
        if current_state not in ["DISCONNECTED", "IDLE", "ERROR"]:
            self.connectBtn.configure(fg_color="lime green")
        else:
            self.connectBtn.configure(fg_color="transparent")
        if current_state == "PLAYING":
            self.playBtn.configure(fg_color="lime green")
            self.pauseBtn.configure(fg_color="transparent")
            self.stopBtn.configure(fg_color="transparent")
        elif current_state == "PAUSED":
            self.pauseBtn.configure(fg_color="yellow3")
            self.playBtn.configure(fg_color="transparent")
            self.stopBtn.configure(fg_color="transparent")
        elif current_state == "STOPPED" or current_state == "READY":
            self.stopBtn.configure(fg_color="red")
            self.playBtn.configure(fg_color="transparent")
            self.pauseBtn.configure(fg_color="transparent")
        else:
            self.playBtn.configure(fg_color="transparent")
            self.pauseBtn.configure(fg_color="transparent")
            self.stopBtn.configure(fg_color="transparent")

    def dropdown_callback(self) -> None:
        self.portsDict = {
            port.device: port
            for port in portList()
            if ((port.pid == 1155 or port.pid == 1163 or port.pid == 1164) and port.vid == 5824)
        }
        if self.portsDict:
            self.portSelect.configure(values=list(self.portsDict.keys()))
        else:
            self.portSelect.configure(values=[])

    def fileHandler(self, event_name="UPLOAD") -> None:
        # file_path = filedialog.askopenfilename(title="Select File", filetypes=[("All Files", "*.*")])
        # if file_path:  # call checking function here or maybe even plot the file
        #     self.requestHandler(event_name, filePath=file_path)
        # else:
        #     messagebox.showwarning("No File Selected", "Please select a file to upload.")
        #     self.fileHandler()
        self.requestHandler(event_name, filePath="file_path_placeholder")

    def requestHandler(self, event_name: str, **kwargs: dict) -> None:
        eventDict = {"event": event_name, "sequence": self.sequence}
        if kwargs:
            eventDict.update(kwargs)
        try:
            self.parentConnection.send(eventDict)
            self.sequence += 1
        except Exception as e:
            print(f"[responseListener]  : {e}")

    def responseListener(self) -> None:
        while self.running:
            try:
                self.response = self.parentConnection.recv()
            except Exception as e:
                print(f"[responseListener]  : {e}")
            if self.response.get("event", None) == "QUIT":
                self.running = False
            else:
                self.after(0, lambda: self.event_generate("<<ReceivedResponse>>", when="tail"))

    def responseHandler(self, VirtualEvent=None) -> None:
        # return
        # print(self.response)
        event = self.response.get("event", None)
        status = self.response.get("status", None)
        if status:
            if event in self.fsm.available_transitions():
                self.fsm.trigger(event)
                # print(self.fsm.available_transitions(), self.fsm.state)
                if event != "QUIT":
                    self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
            else:
                raise ValueError(f"Event {event} not in: {self.fsm.available_transitions()}")
        else:
            print(f"NAK : {self.response}")

        self.response = {}

    def run(self) -> None:
        self.comProcess.start()
        self.resLT.start()
        self.mainloop()

    def on_closing(self) -> None:
        self.requestHandler("QUIT")
        if self.resLT.is_alive():
            self.resLT.join()
        self.comProcess.join()
        self.parentConnection.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.run()
    print("Done.")
