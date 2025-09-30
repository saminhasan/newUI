import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont


class LogViewer(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # internal state: list of dicts {"tag":..., "entry":...}
        self.logs = []
        self.offset = 0

        # 1) Textbox without its own scrollbars
        self.textbox = ctk.CTkTextbox(self, wrap="none", state="disabled", activate_scrollbars=False)
        self.textbox.grid(row=0, column=0, sticky="nsew")

        # 1a) Tag configurations
        self.textbox.tag_config("INFO", foreground="green")
        self.textbox.tag_config("WARNING", foreground="orange")
        self.textbox.tag_config("ERROR", foreground="red")
        self.textbox.tag_config("DEBUG", foreground="gray")

        # 2) External vertical scrollbar
        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self._on_scroll)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # 3) Make grid expandable
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 4) Determine line height for slicing
        tk_font = tkfont.Font(font=self.textbox.cget("font"))
        self.line_height = tk_font.metrics("linespace")

        # 5) Re-render on resize
        self.textbox.bind("<Configure>", lambda e: self._refresh_view())

        # 6) Mouse-wheel on toplevel
        top = self.winfo_toplevel()
        top.bind("<MouseWheel>", self._on_mousewheel)  # Windows
        top.bind("<Button-4>", self._on_mousewheel)  # Linux up
        top.bind("<Button-5>", self._on_mousewheel)  # Linux down

    def update_log(self, log_dict: dict):
        """
        Add a new log entry.
        log_dict must have:
          - "tag":    one of "INFO","WARNING","ERROR","DEBUG"
          - "entry":  the text message
        """
        tag = log_dict.get("tag", "INFO")
        entry = log_dict.get("entry", "")
        # determine if we're scrolled to bottom
        at_bottom = self.offset + self._visible_count() >= len(self.logs)
        self.logs.append({"tag": tag, "entry": entry})
        if at_bottom:
            # auto-scroll to show the new line
            self.offset = max(0, len(self.logs) - self._visible_count())
        self._refresh_view()

    def _visible_count(self):
        h = self.textbox.winfo_height()
        return max(1, h // self.line_height) if h > 1 else 1

    def _refresh_view(self):
        visible = self._visible_count()
        total = len(self.logs)
        max_off = max(0, total - visible)
        self.offset = min(max(self.offset, 0), max_off)

        # redraw only visible slice
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        for item in self.logs[self.offset : self.offset + visible]:
            text = item["entry"] + "\n"
            tag = item.get("tag", "info")
            self.textbox.insert("end", text, tag)
        self.textbox.configure(state="disabled")

        # update scrollbar thumb
        if total:
            first = self.offset / total
            last = (self.offset + visible) / total
            self.scrollbar.set(first, last)
        else:
            self.scrollbar.set(0, 1)

    def _on_scroll(self, *args):
        total = len(self.logs)
        visible = self._visible_count()
        max_off = max(0, total - visible)

        if args[0] == "moveto":
            frac = float(args[1])
            self.offset = min(int(frac * total), max_off)
        elif args[0] == "scroll":
            amt, what = int(args[1]), args[2]
            if what == "units":
                self.offset += amt
            elif what == "pages":
                self.offset += amt * visible

        self._refresh_view()

    def _on_mousewheel(self, event):
        if hasattr(event, "delta"):
            delta = -1 if event.delta > 0 else 1
        else:
            delta = -3 if event.num == 4 else 3
        self.offset += delta
        self._refresh_view()


if __name__ == "__main__":
    # Demo
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("500x400")

    viewer = LogViewer(root)
    viewer.pack(fill="both", expand=True, padx=10, pady=10)

    # test a mix of tags
    import random

    tags = ["info", "warning", "error", "debug"]

    def feed(i=1):
        viewer.update_log({"tag": random.choice(tags), "entry": f"Live entry #{i}"})
        root.after(500, lambda: feed(i + 1))

    feed()

    root.mainloop()
