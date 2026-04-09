import tkinter as tk

class TitleBar(tk.Frame):
    """
    A specialized TitleBar component for the Audio Extractor.
    Encapsulates window controls: Close, Minimize, and Always on Top.
    """
    def __init__(self, master, title_text="Audio Extractor",
                 bg_color="#1e1e1e", accent_color="#007acc",
                 fg_color="#ffffff", fg_dim="#888888"):
        # Initialize the frame as a subclass of tk.Frame
        super().__init__(master, bg=bg_color, height=36)
        self.pack(fill="x", side="top")
        self.pack_propagate(False)

        self.master = master
        self.bg_color = bg_color
        self.accent_color = accent_color
        self.fg_color = fg_color
        self.fg_dim = fg_dim
        self._always_on_top = [False]

        # 1. Title Label
        title_font = ("Segoe UI", 10, "bold") if master.winfo_class() != "Darwin" else ("SF Pro Display", 12, "bold")
        self.title_label = tk.Label(
            self, text=title_text,
            bg=bg_color, fg=accent_color, font=title_font,
            padx=14
        )
        self.title_label.pack(side="left")

        # 2. Button Container (to hold the right-aligned buttons)
        self.controls_frame = tk.Frame(self, bg=bg_color)
        self.controls_frame.pack(side="right")

        # 3. Close Button
        self.close_btn = tk.Button(
            self.controls_frame, text="✕",
            command=self._close,
            bg=bg_color, fg=fg_dim, font=("Segoe UI", 13),
            relief="flat", cursor="hand2", padx=10, pady=4,
            activebackground=bg_color, activeforeground=accent_color,
        )
        self.close_btn.pack(side="right")

        # 4. Minimize Button
        self.min_btn = tk.Button(
            self.controls_frame, text="−",
            command=self._minimize,
            bg=bg_color, fg=fg_dim, font=("Segoe UI", 13),
            relief="flat", cursor="hand2", padx=10, pady=4,
            activebackground=bg_color, activeforeground=accent_color        
        )
        self.min_btn.pack(side="right")

        # 5. Always On Top Button
        self.btn_top = tk.Button(
            self.controls_frame, text="⊤",
            command=self._toggle_ontop,
            bg=bg_color, fg=fg_dim,
            font=("Segoe UI", 11),
            relief="flat", cursor="hand2", padx=10, pady=4,
            activebackground=bg_color, activeforeground=fg_color            
        )

        def _tb_press(e):
            _drag["x"] = e.x_root - self.master.winfo_x()
            _drag["y"] = e.y_root - self.master.winfo_y()
            _drag["dragging"] = False
        
        def _tb_drag(e):
            _drag["dragging"] = True
            self.master.geometry(f"+{e.x_root - _drag['x']}+{e.y_root - _drag['y']}")

        self.btn_top.pack(side="right")
        _drag = {"x": 0, "y": 0, "dragging": False}
        self.bind("<ButtonPress-1>", _tb_press)
        self.bind("<B1-Motion>", _tb_drag)

    def _close(self):
        self.master.destroy()

    def _minimize(self):
        self.master.withdraw()
        self.master.after(200, self.master.deiconify)

    def _toggle_ontop(self):
        self._always_on_top[0] = not self._always_on_top[0]
        self.master.wm_attributes("-topmost", self._always_on_top[0])
        # Update button color to reflect state
        new_fg = self.accent_color if self._always_on_top[0] else self.fg_dim
        self.btn_top.config(fg=new_fg)
