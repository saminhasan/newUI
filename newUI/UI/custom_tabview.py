import customtkinter as ctk


class CustomTabview(ctk.CTkTabview):
    """
    Custom TabView that applies specific styling modifications automatically.
    Inherits from CTkTabview and applies custom spacing, colors, and positioning.
    """
    
    def __init__(self, master, **kwargs):
        # Set default corner_radius to 0 if not specified
        if "corner_radius" not in kwargs:
            kwargs["corner_radius"] = 0
            
        super().__init__(master, **kwargs)
        
        # Apply the custom modifications after initialization
        self._apply_custom_modifications()
    
    def _apply_custom_modifications(self):
        """Apply all the custom styling modifications"""
        
        # Remove gaps between button and frame
        self._outer_spacing = 0
        self._outer_button_overhang = self._button_height
        
        # Get colors for styling
        fg_color = self.cget("fg_color")
        bg_color = self.cget("bg_color")
        
        # Configure segmented button styling
        self._segmented_button.configure(
            fg_color=fg_color,
            selected_color=fg_color,        # Selected tab uses lighter color
            unselected_color=bg_color,      # Unselected tabs blend with dark background
            border_width=0,                 # Remove borders
            corner_radius=0,                # Square corners
            selected_hover_color=fg_color   # Keep selected color on hover
        )
        
        # Reposition segmented button (left-aligned, no padding)
        self._segmented_button.grid_forget()
        self._segmented_button.grid(row=1, rowspan=2, column=0, columnspan=1, 
                                  padx=0, sticky="nw")
        
        # Reconfigure grid to apply new spacing
        self._configure_grid()
    
    def add(self, name: str):
        """Override add method to apply modifications after adding tabs"""
        result = super().add(name)
        # Reapply modifications in case they were reset
        self._apply_custom_modifications()
        return result
    
    def insert(self, index: int, name: str):
        """Override insert method to apply modifications after inserting tabs"""
        result = super().insert(index, name)
        # Reapply modifications in case they were reset
        self._apply_custom_modifications()
        return result
