import customtkinter as ctk
from model import FSM, states, transitions
from PIL import Image


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.buttons = {}
        self.image_label = None

        self.title("FSM Example")
        self.geometry("1280x720")
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.frame = ctk.CTkFrame(master=self, corner_radius=10)
        self.frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.control_frame = ctk.CTkFrame(master=self, corner_radius=10)
        self.control_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        # Initialize the FSM
        self.fsm = FSM(initial="IDLE")
        self.create_ui()

    def create_ui(self):

        triggers = {trigger["transition"] for trigger in transitions}
        self.control_frame.grid_columnconfigure(0, weight=1)
        for idx in range(len(triggers)):
            self.control_frame.grid_rowconfigure(idx, weight=1)
        # self.control_frame.grid_rowconfigure(0, weight=1)
        for idx, trigger in enumerate(triggers):
            button = ctk.CTkButton(
                master=self.control_frame,
                text=trigger,
                command=lambda t=trigger: self.trigger_action(t),
            )
            button.grid(row=idx, column=0, padx=5, pady=5, sticky="nsew")
            self.buttons[trigger] = button

    def trigger_action(self, trigger):
        try:
            current_state = self.fsm.state
            new_state = self.fsm.trigger(trigger)
            print(f"{current_state}----{trigger}---->{new_state}")
        except ValueError as e:
            print(e)
        self.update_ui()

    def update_ui(self):
        for trigger in self.buttons:
            if trigger in self.fsm.available_transitions():
                self.buttons[trigger].configure(state="normal", fg_color="green", hover_color="darkgreen")
            else:
                self.buttons[trigger].configure(state="disabled", fg_color="red", hover_color="darkred")

        # Update the title with the current state
        self.title(f"FSM Example - Current State: {self.fsm.state}")
        print(f"FSM Example - Current State: {self.fsm.state}")

        # Generate the FSM diagram and display it
        try:
            png_data = self.fsm.draw()  # This returns binary PNG data

            # Use BytesIO to create a file-like object from binary data
            from io import BytesIO

            img = Image.open(BytesIO(png_data))

            # Get the frame size to scale the image appropriately
            self.frame.update_idletasks()  # Make sure frame size is updated
            frame_width = self.frame.winfo_width()  # Account for padding
            frame_height = self.frame.winfo_height()  # Account for padding

            # Calculate scaling to maintain aspect ratio
            img_width, img_height = img.size
            scale_x = frame_width / img_width
            scale_y = frame_height / img_height
            scale = min(scale_x, scale_y, 1.0)  # Don't scale up, only down

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # Create CTkImage from PIL Image with calculated size
            ctk_image = ctk.CTkImage(img, size=(new_width, new_height))

            # Create or update the image label
            if self.image_label is None:
                self.image_label = ctk.CTkLabel(master=self.frame, image=ctk_image, text="")
                self.image_label.pack(expand=True, fill="both", padx=10, pady=10)
            else:
                self.image_label.configure(image=ctk_image)

        except Exception as e:
            print(f"Error displaying FSM diagram: {e}")
            # Show a fallback text if image fails
            if self.image_label is None:
                self.image_label = ctk.CTkLabel(master=self.frame, text=f"Current State: {self.fsm.state}")
                self.image_label.pack(expand=True, fill="both", padx=10, pady=10)
            else:
                self.image_label.configure(text=f"Current State: {self.fsm.state}", image=None)

    def run(self):
        self.update()
        self.update_ui()
        self.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
