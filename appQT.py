import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QPushButton,
    QComboBox,
    QTextEdit,
    QFrame,
    QButtonGroup,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QTextCursor, QColor
from multiprocessing import Process, Pipe, Queue
from threading import Thread, Event
from appModel import FSM
import time
from serial_process import serialServer, portList
from queue import Empty

WIDTH = 960
HEIGHT = 480
MAX_LINES = 100


class ResponseListenerThread(QThread):
    response_received = pyqtSignal(dict)

    def __init__(self, parent_connection, parent):
        super().__init__()
        self.parent_connection = parent_connection
        self.running = True
        self.parent_app = parent

    def run(self):
        while self.running and self.parent_app.running:
            try:
                response = self.parent_connection.recv()
                if response.get("event", None) == "quit":
                    break
                else:
                    self.response_received.emit(response)
            except:
                break

    def stop(self):
        self.running = False


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.seq = 0
        self.running = True
        self.response = {}
        self.recvQ = Queue()
        self.parentConnection, self.childConnection = Pipe()
        self.fsm = FSM()

        self.setup_ui()
        self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)

        # Initialize communication components
        self.comServer = serialServer(self.childConnection, self.recvQ)
        self.comProcess = Process(target=self.comServer.run, name="SerialServerProcess")

        # Setup response listener thread
        self.resLT = ResponseListenerThread(self.parentConnection, self)
        self.resLT.response_received.connect(self.responseHandler)

        # Setup data handler timer
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.dataHandler)

        # Setup ports dictionary
        self.portsDict = {}

    def setup_ui(self):
        self.setWindowTitle("UI")
        self.setGeometry(100, 100, WIDTH, HEIGHT)
        self.setMinimumSize(WIDTH, HEIGHT)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left side - Tabs
        self.tabL = QTabWidget()
        main_layout.addWidget(self.tabL, 5)

        # Log Tab
        self.logTab = QWidget()
        self.tabL.addTab(self.logTab, "  Log  ")
        log_layout = QVBoxLayout(self.logTab)

        self.logTerminal = QTextEdit()
        self.logTerminal.setReadOnly(True)
        self.logTerminal.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.logTerminal)

        # State Tab
        self.stateTab = QWidget()
        self.tabL.addTab(self.stateTab, "  State  ")

        # Data Tab
        self.dataTab = QWidget()
        self.tabL.addTab(self.dataTab, "  Data  ")

        # Right side - Control Panel
        self.tabR = QTabWidget()
        main_layout.addWidget(self.tabR, 0)

        self.controlPanel = QWidget()
        self.tabR.addTab(self.controlPanel, "Control Panel")

        # Control panel layout
        control_layout = QGridLayout(self.controlPanel)
        self.controlPanelWidgets = {}

        # Configure row and column stretch factors (like tkinter's weight)
        for col in range(6):
            control_layout.setColumnStretch(col, 1)
        for row in range(1, 10):
            control_layout.setRowStretch(row, 1)

        # Port selection
        self.portSelect = QComboBox()
        self.portSelect.setMinimumWidth(280)
        self.portSelect.activated.connect(self.on_port_selected)
        control_layout.addWidget(self.portSelect, 0, 0, 1, 3)
        self.controlPanelWidgets["portSelect"] = self.portSelect

        # Connection buttons
        connection_frame = QFrame()
        connection_layout = QHBoxLayout(connection_frame)
        connection_layout.setContentsMargins(0, 0, 0, 0)

        self.connectBtn = QPushButton("C")
        self.disconnectBtn = QPushButton("D")
        self.connectBtn.clicked.connect(lambda: self.requestHandler("connect"))
        self.disconnectBtn.clicked.connect(lambda: self.requestHandler("disconnect"))

        connection_layout.addWidget(self.connectBtn)
        connection_layout.addWidget(self.disconnectBtn)
        control_layout.addWidget(connection_frame, 0, 4, 1, 2)

        self.controlPanelWidgets["connect"] = self.connectBtn
        self.controlPanelWidgets["disconnect"] = self.disconnectBtn

        # Enable button - will now expand to fill available space
        self.enableBtn = QPushButton("ENABLE")
        self.enableBtn.clicked.connect(lambda: self.requestHandler("enable"))
        control_layout.addWidget(self.enableBtn, 1, 0, 2, 6)
        self.controlPanelWidgets["enable"] = self.enableBtn

        # Upload button - will now expand to fill available space
        self.uploadBtn = QPushButton("UPLOAD")
        self.uploadBtn.clicked.connect(lambda: self.fileHandler("upload"))
        control_layout.addWidget(self.uploadBtn, 3, 0, 2, 6)
        self.controlPanelWidgets["upload"] = self.uploadBtn

        # Playback controls
        playback_frame = QFrame()
        playback_layout = QHBoxLayout(playback_frame)
        playback_layout.setContentsMargins(0, 0, 0, 0)

        self.playBtn = QPushButton("▶")
        self.pauseBtn = QPushButton("||")
        self.stopBtn = QPushButton("■")

        playback_font = QFont("Cascadia Code", 16)
        self.playBtn.setFont(playback_font)
        self.pauseBtn.setFont(playback_font)
        self.stopBtn.setFont(playback_font)

        self.playBtn.clicked.connect(lambda: self.requestHandler("play"))
        self.pauseBtn.clicked.connect(lambda: self.requestHandler("pause"))
        self.stopBtn.clicked.connect(lambda: self.requestHandler("stop"))

        playback_layout.addWidget(self.playBtn)
        playback_layout.addWidget(self.pauseBtn)
        playback_layout.addWidget(self.stopBtn)
        control_layout.addWidget(playback_frame, 5, 0, 2, 6)

        self.controlPanelWidgets["play"] = self.playBtn
        self.controlPanelWidgets["pause"] = self.pauseBtn
        self.controlPanelWidgets["stop"] = self.stopBtn

        # Disable button (EStop)
        self.disableBtn = QPushButton("EStop")
        self.disableBtn.setStyleSheet("QPushButton { background-color: #8B0000; color: white; }")
        self.disableBtn.clicked.connect(lambda: self.requestHandler("disable"))
        control_layout.addWidget(self.disableBtn, 7, 0, 2, 6)
        self.controlPanelWidgets["disable"] = self.disableBtn

        # Reset button
        self.resetBtn = QPushButton("RESET")
        self.resetBtn.clicked.connect(lambda: self.requestHandler("reset"))
        control_layout.addWidget(self.resetBtn, 9, 0, 1, 6)
        self.controlPanelWidgets["reset"] = self.resetBtn

        # Setup dropdown callback
        self.portSelect.showPopup = self.dropdown_callback_wrapper

    def dropdown_callback_wrapper(self):
        self.dropdown_callback()
        QComboBox.showPopup(self.portSelect)

    def configure_widgets(self, to_enable=None, current_state=None):
        enabled_widgets = set(to_enable or ())
        for key, widget in self.controlPanelWidgets.items():
            if key not in enabled_widgets:
                widget.setEnabled(False)
            else:
                widget.setEnabled(True)

    def dropdown_callback(self):
        self.portsDict = {
            port.device: port
            for port in portList()
            if ((port.pid == 1155 or port.pid == 1163 or port.pid == 1164) and port.vid == 5824)
        }
        if self.portsDict:
            self.portSelect.clear()
            self.portSelect.addItems(list(self.portsDict.keys()))
        else:
            self.portSelect.clear()

    def on_port_selected(self, index):
        if self.portSelect.count() > 0:
            port = self.portSelect.currentText()
            self.requestHandler("portSelect", port=port)

    def fileHandler(self, event_name="upload"):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*.*)")
        if file_path:
            self.requestHandler(event_name, filePath=file_path)
        else:
            QMessageBox.warning(self, "No File Selected", "Please select a file to upload.")
            self.fileHandler()

    def requestHandler(self, event_name, **kwargs):
        eventDict = {"event": event_name, "seq": self.seq}
        if kwargs:
            eventDict.update(kwargs)
        self.parentConnection.send(eventDict)
        self.seq += 1

    def responseHandler(self, response):
        self.response = response
        event = self.response.get("event", None)
        if event is not None:
            if event in self.fsm.available_transitions():
                self.fsm.trigger(event)
                if event != "quit":
                    self.configure_widgets(self.fsm.available_transitions(), self.fsm.state)
            else:
                raise Exception(f"Event {event} not in: {self.fsm.available_transitions()}")
        self.response = {}

    def dataHandler(self):
        data = []
        while not self.recvQ.empty():
            try:
                data.append(self.recvQ.get_nowait())
            except Empty:
                pass

        if self.running:
            if data:
                self.updateLog(data)

    def updateLog(self, data):
        # Format data efficiently
        data_str = "".join(f"{item['tag']}:{item['entry']}" for item in data)

        # Get current cursor position and check if at end
        cursor = self.logTerminal.textCursor()
        at_end = cursor.atEnd()

        # Move to end and insert text
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(data_str)

        # Auto-scroll if was at end
        if at_end:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.logTerminal.setTextCursor(cursor)

    def run(self):
        self.comProcess.start()
        self.resLT.start()
        self.data_timer.start(10)  # 10ms timer for data handling
        self.show()

    def closeEvent(self, event):
        self.on_closing()
        event.accept()

    def on_closing(self):
        self.running = False
        self.requestHandler("quit")

        if self.resLT.isRunning():
            self.resLT.stop()
            self.resLT.wait()

        self.dataHandler()  # Final data processing
        self.data_timer.stop()

        if self.comProcess.is_alive():
            self.comProcess.join()

        self.parentConnection.close()
        self.recvQ.close()
        self.recvQ.join_thread()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = App()
    main_app.run()
    sys.exit(app.exec())
