import customtkinter as ctk


class CustomComboBox(ctk.CTkComboBox):
    """
    Custom ComboBox that supports dynamic option generation when dropdown is pressed.
    Inherits from CTkComboBox and adds a callback for when the dropdown button is clicked.
    """

    def __init__(self, master, dropdown_pressed_callback=None, **kwargs):
        # Store the original command before calling super().__init__
        self._original_command = kwargs.get("command", None)

        # Replace the command with our wrapper
        if self._original_command is not None:
            kwargs["command"] = self._command_wrapper

        super().__init__(master, **kwargs)
        self._dropdown_pressed_callback = dropdown_pressed_callback
        self._setup_dropdown_callback()

    def _command_wrapper(self, value):
        """Wrapper for the command callback that enforces readonly state"""
        # Call the original command if it exists
        if self._original_command is not None:
            self._original_command(value)

        # Force readonly state after command execution
        self._entry.configure(state="readonly")

    def _setup_dropdown_callback(self):
        original_open_dropdown = self._open_dropdown_menu

        def custom_open_dropdown():
            if self._dropdown_pressed_callback is not None:
                self._dropdown_pressed_callback()
            original_open_dropdown()

        self._open_dropdown_menu = custom_open_dropdown

    def set_dropdown_pressed_callback(self, callback):
        """
        Set or update the callback function that gets called when dropdown is pressed.

        Args:
            callback: Function to call when dropdown button is pressed.
                     Should take no arguments.
        """
        self._dropdown_pressed_callback = callback

    def configure(self, **kwargs):
        """Override configure to handle the new dropdown_pressed_callback parameter"""
        if "dropdown_pressed_callback" in kwargs:
            self._dropdown_pressed_callback = kwargs.pop("dropdown_pressed_callback")
        super().configure(**kwargs)
