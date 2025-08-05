"""
Hexapod Controller UI - Clean Version
Provides the same functionality as appUI_r.py with improved code organization
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from multiprocessing import Process, Pipe
from threading import Thread
from typing import Dict, Set, Optional, List

from UI.custom_combobox import CustomComboBox
from serial.tools import list_ports, list_ports_common
from appModel import FSM
from serial_process import serialServer


class HexapodController(ctk.CTk):
    """Main application window for the Hexapod Controller"""

    # Constants
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 480
    GRID_COLUMNS = 6
    GRID_ROWS = 10

    # USB device filtering (Teensy devices)
    TEENSY_VID = 5824
    TEENSY_PIDS = {1155, 1163, 1164}

    def __init__(self):
        super().__init__()

        # Core application state
        self.running = True
        self.response = {}

        # Communication setup
        self.parent_connection, self.child_connection = Pipe()

        # State machine
        self.fsm = FSM()

        # Process and thread references
        self.response_thread: Optional[Thread] = None
        self.serial_server: Optional[serialServer] = None
        self.serial_process: Optional[Process] = None

        # UI components
        self.control_panel_widgets: Dict[str, ctk.CTkWidget] = {}
        self.ports_dict: Dict[str, list_ports_common.ListPortInfo] = {}

        # Initialize UI and setup
        self._load_icons()
        self._setup_window()
        self._create_widgets()
        self._setup_communication()
        self._configure_initial_state()

    def _load_icons(self) -> None:
        """Load all required icons"""
        try:
            self.icons = {
                "usb": Image.open("Icons/usb.png"),
                "usb_off": Image.open("Icons/usb_off.png"),
                "play": Image.open("Icons/play.png"),
                "pause": Image.open("Icons/pause.png"),
                "stop": Image.open("Icons/stop.png"),
            }
        except FileNotFoundError as e:
            print(f"Warning: Could not load icon: {e}")
            self.icons = {}

    def _setup_window(self) -> None:
        """Configure main window properties"""
        self.title("Hexapod Controller")
        self.resizable(True, True)
        self.minsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Configure main grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _create_widgets(self) -> None:
        """Create and layout all UI widgets"""
        self._create_main_panel()
        self._create_port_selector()
        self._create_connection_controls()
        self._create_action_buttons()
        self._create_playback_controls()
        self._create_emergency_controls()

    def _create_main_panel(self) -> None:
        """Create the main control panel"""
        self.control_panel = ctk.CTkFrame(self, corner_radius=10)
        self.control_panel.grid(row=0, column=0, sticky="nsew")

        # Configure grid layout
        for col in range(self.GRID_COLUMNS):
            self.control_panel.grid_columnconfigure(col, weight=1)
        for row in range(self.GRID_ROWS):
            self.control_panel.grid_rowconfigure(row, weight=1)

    def _create_port_selector(self) -> None:
        """Create the COM port selection dropdown"""
        self.port_select = CustomComboBox(
            self.control_panel,
            values=[""],
            dropdown_pressed_callback=self._refresh_ports,
            width=280,
            state="readonly",
            command=lambda port: self._handle_request("portSelect", port=port),
        )
        self.port_select.grid(row=0, column=0, columnspan=3, sticky="we", padx=(10, 5), pady=(10, 10))
        self.control_panel_widgets["portSelect"] = self.port_select

    def _create_connection_controls(self) -> None:
        """Create connection/disconnection buttons"""
        # Connection frame
        connection_frame = ctk.CTkFrame(self.control_panel)
        connection_frame.grid(row=0, column=4, columnspan=2, sticky="we", padx=(5, 10), pady=(10, 10))
        connection_frame.grid_columnconfigure(0, weight=1)
        connection_frame.grid_columnconfigure(1, weight=1)

        # Connect button
        connect_btn = self._create_icon_button(
            connection_frame, icon_key="usb", command=lambda: self._handle_request("connect"), hover_color="green4"
        )
        connect_btn.grid(row=0, column=0, sticky="nsew", padx=(5, 2.5), pady=5)
        self.control_panel_widgets["connect"] = connect_btn

        # Disconnect button
        disconnect_btn = self._create_icon_button(
            connection_frame, icon_key="usb_off", command=lambda: self._handle_request("disconnect"), hover_color="red"
        )
        disconnect_btn.grid(row=0, column=1, sticky="nsew", padx=(2.5, 5), pady=5)
        self.control_panel_widgets["disconnect"] = disconnect_btn

    def _create_action_buttons(self) -> None:
        """Create main action buttons (Enable, Upload)"""
        # Enable button
        enable_btn = ctk.CTkButton(self.control_panel, text="ENABLE", command=lambda: self._handle_request("enable"))
        enable_btn.grid(row=1, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.control_panel_widgets["enable"] = enable_btn

        # Upload button
        upload_btn = ctk.CTkButton(self.control_panel, text="UPLOAD", command=lambda: self._handle_file_upload("upload"))
        upload_btn.grid(row=3, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.control_panel_widgets["upload"] = upload_btn

    def _create_playback_controls(self) -> None:
        """Create playback control buttons (Play, Pause, Stop)"""
        playback_frame = ctk.CTkFrame(self.control_panel)
        playback_frame.grid(row=5, column=0, columnspan=6, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))

        # Configure playback frame grid
        for col in range(3):
            playback_frame.grid_columnconfigure(col, weight=1)
        playback_frame.grid_rowconfigure(0, weight=1)

        # Play button
        play_btn = self._create_icon_button(
            playback_frame, icon_key="play", command=lambda: self._handle_request("play"), hover_color="dark green"
        )
        play_btn.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.control_panel_widgets["play"] = play_btn

        # Pause button
        pause_btn = self._create_icon_button(
            playback_frame, icon_key="pause", command=lambda: self._handle_request("pause"), hover_color="yellow4"
        )
        pause_btn.grid(row=0, column=1, sticky="nsew", padx=(5, 5), pady=10)
        self.control_panel_widgets["pause"] = pause_btn

        # Stop button
        stop_btn = self._create_icon_button(
            playback_frame, icon_key="stop", command=lambda: self._handle_request("stop"), hover_color="red4"
        )
        stop_btn.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
        self.control_panel_widgets["stop"] = stop_btn

    def _create_emergency_controls(self) -> None:
        """Create emergency stop and reset buttons"""
        # Emergency stop button
        disable_btn = ctk.CTkButton(
            self.control_panel,
            text="EStop",
            command=lambda: self._handle_request("disable"),
            fg_color="red4",
            hover_color="red2",
        )
        disable_btn.grid(row=7, column=0, rowspan=2, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.control_panel_widgets["disable"] = disable_btn

        # Reset button
        reset_btn = ctk.CTkButton(self.control_panel, text="RESET", command=lambda: self._handle_request("reset"))
        reset_btn.grid(row=9, column=0, columnspan=6, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self.control_panel_widgets["reset"] = reset_btn

    def _create_icon_button(self, parent, icon_key: str, command: callable, hover_color: str) -> ctk.CTkButton:
        """Helper method to create buttons with icons"""
        kwargs = {"text": "", "command": command, "hover_color": hover_color, "fg_color": "transparent"}

        if icon_key in self.icons:
            kwargs["image"] = ctk.CTkImage(light_image=self.icons[icon_key], dark_image=self.icons[icon_key])

        return ctk.CTkButton(parent, **kwargs)

    def _setup_communication(self) -> None:
        """Initialize communication components"""
        # Create serial server and process
        self.serial_server = serialServer(self.child_connection)
        self.serial_process = Process(target=self.serial_server.run, name="SerialServerProcess")

        # Create response listener thread
        self.response_thread = Thread(target=self._response_listener, daemon=True, name="ResponseListenerThread")

        # Bind response handler
        self.bind("<<ReceivedResponse>>", self._handle_response)

    def _configure_initial_state(self) -> None:
        """Configure initial widget states based on FSM"""
        self._update_widget_states(self.fsm.available_transitions(), self.fsm.state)

    def _refresh_ports(self) -> None:
        """Refresh the list of available COM ports"""
        self.ports_dict = {
            port.device: port
            for port in list_ports.comports()
            if (port.pid in self.TEENSY_PIDS and port.vid == self.TEENSY_VID)
        }

        port_names = list(self.ports_dict.keys()) if self.ports_dict else []
        self.port_select.configure(values=port_names)

    def _handle_file_upload(self, event_name: str = "upload") -> None:
        """Handle file upload dialog and request"""
        # Placeholder implementation - uncomment for actual file dialog
        # file_path = filedialog.askopenfilename(
        #     title="Select File",
        #     filetypes=[("All Files", "*.*")]
        # )
        # if file_path:
        #     self._handle_request(event_name, filePath=file_path)
        # else:
        #     messagebox.showwarning("No File Selected", "Please select a file to upload.")
        #     return self._handle_file_upload(event_name)

        # Placeholder for now
        self._handle_request(event_name, filePath="file_path_placeholder")

    def _handle_request(self, event_name: str, **kwargs) -> None:
        """Send a request to the serial process"""
        event_dict = {"event": event_name}
        if kwargs:
            event_dict.update(kwargs)

        try:
            self.parent_connection.send(event_dict)
        except Exception as e:
            print(f"Error sending request: {e}")

    def _response_listener(self) -> None:
        """Listen for responses from the serial process"""
        while self.running:
            try:
                self.response = self.parent_connection.recv()
                if self.response.get("event") == "quit":
                    break
                else:
                    # Schedule response handling on main thread
                    self.after(0, lambda: self.event_generate("<<ReceivedResponse>>", when="tail"))
            except Exception as e:
                if self.running:  # Only log if we're still running
                    print(f"Error in response listener: {e}")
                break

    def _handle_response(self, event=None) -> None:
        """Handle responses from the serial process"""
        if not self.response:
            return

        event_name = self.response.get("event")
        if not event_name:
            self.response = {}
            return

        try:
            if event_name in self.fsm.available_transitions():
                self.fsm.trigger(event_name)
                if event_name != "quit":
                    self._update_widget_states(self.fsm.available_transitions(), self.fsm.state)
            else:
                print(f"Warning: Event '{event_name}' not in available transitions: {self.fsm.available_transitions()}")
        except Exception as e:
            print(f"Error handling response: {e}")
        finally:
            self.response = {}

    def _update_widget_states(self, enabled_widgets: Set[str], current_state: str) -> None:
        """Update widget enabled/disabled states and visual indicators"""
        enabled_set = set(enabled_widgets or [])

        # Update enabled/disabled states
        for widget_key, widget in self.control_panel_widgets.items():
            target_state = "normal" if widget_key in enabled_set else "disabled"
            if widget.cget("state") != target_state:
                widget.configure(state=target_state)

        # Update visual state indicators
        self._update_connection_indicator(current_state)
        self._update_playback_indicators(current_state)

    def _update_connection_indicator(self, current_state: str) -> None:
        """Update connection button visual state"""
        if "connect" in self.control_panel_widgets:
            connected_states = {"DISCONNECTED", "IDLE", "ERROR"}
            color = "transparent" if current_state in connected_states else "lime green"
            self.control_panel_widgets["connect"].configure(fg_color=color)

    def _update_playback_indicators(self, current_state: str) -> None:
        """Update playback button visual states"""
        playback_widgets = ["play", "pause", "stop"]

        # Reset all to transparent
        for widget_key in playback_widgets:
            if widget_key in self.control_panel_widgets:
                self.control_panel_widgets[widget_key].configure(fg_color="transparent")

        # Set active state color
        state_colors = {"PLAYING": ("play", "lime green"), "PAUSED": ("pause", "yellow3"), "STOPPED": ("stop", "red")}

        if current_state in state_colors:
            widget_key, color = state_colors[current_state]
            if widget_key in self.control_panel_widgets:
                self.control_panel_widgets[widget_key].configure(fg_color=color)

    def run(self) -> None:
        """Start the application"""
        try:
            # Start communication components
            if self.serial_process:
                self.serial_process.start()
            if self.response_thread:
                self.response_thread.start()

            # Start main loop
            self.mainloop()
        except Exception as e:
            print(f"Error running application: {e}")
            self._cleanup()

    def _on_closing(self) -> None:
        """Handle application closing"""
        self.running = False
        self._handle_request("quit")
        self._cleanup()
        self.destroy()

    def _cleanup(self) -> None:
        """Clean up resources"""
        try:
            # Wait for response thread
            if self.response_thread and self.response_thread.is_alive():
                self.response_thread.join(timeout=2.0)

            # Close connection
            if hasattr(self, "parent_connection"):
                self.parent_connection.close()

            # Wait for serial process
            if self.serial_process and self.serial_process.is_alive():
                self.serial_process.join(timeout=5.0)
                if self.serial_process.is_alive():
                    self.serial_process.terminate()
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    try:
        app = HexapodController()
        app.run()
        print("Application completed successfully.")
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
