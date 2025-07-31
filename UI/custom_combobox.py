import customtkinter as ctk


class CustomComboBox(ctk.CTkComboBox):
    """
    Custom ComboBox that supports dynamic option generation when dropdown is pressed.
    Inherits from CTkComboBox and adds a callback for when the dropdown button is clicked.
    """
    
    def __init__(self, master, dropdown_pressed_callback=None, readonly=True, **kwargs):
        # Set state to readonly if readonly=True
        if readonly and "state" not in kwargs:
            kwargs["state"] = "readonly"
            
        super().__init__(master, **kwargs)
        # Store the callback function
        self._dropdown_pressed_callback = dropdown_pressed_callback
        
        # Apply the custom modification
        self._setup_dropdown_callback()
    
    def _setup_dropdown_callback(self):
        """Override the _open_dropdown_menu method to add custom behavior"""
        # Store the original method
        original_open_dropdown = self._open_dropdown_menu
        
        def custom_open_dropdown():
            # Call the custom callback first (if provided)
            if self._dropdown_pressed_callback is not None:
                self._dropdown_pressed_callback()
            
            # Then call the original method to open the dropdown
            original_open_dropdown()
        
        # Replace the original method with our custom one
        self._open_dropdown_menu = custom_open_dropdown
    
    def set_dropdown_pressed_callback(self, callback):
        """
        Set or update the callback function that gets called when dropdown is pressed.
        
        Args:
            callback: Function to call when dropdown button is pressed.
                     Should take no arguments.
        """
        self._dropdown_pressed_callback = callback
    
    def set_readonly(self, readonly=True):
        """
        Set the combobox to readonly mode to prevent user text input.
        
        Args:
            readonly (bool): If True, prevents user from typing in the entry.
                           If False, allows user to type custom values.
        """
        if readonly:
            self.configure(state="readonly")
        else:
            self.configure(state="normal")
    
    def configure(self, **kwargs):
        """Override configure to handle the new dropdown_pressed_callback parameter"""
        if "dropdown_pressed_callback" in kwargs:
            self._dropdown_pressed_callback = kwargs.pop("dropdown_pressed_callback")
        
        super().configure(**kwargs)
