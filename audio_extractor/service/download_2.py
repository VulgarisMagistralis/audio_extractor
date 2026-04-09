import os
import threading
import tkinter as tk
from tkinter import messagebox
from audio_extractor.button_state import ButtonState
from audio_extractor.utils import check_dependencies
from audio_extractor.downloader import build_ydl_opts, run_download

class DownloadManager:
    """
    Controller class that encapsulates all dependencies for the download process.
    """
    def __init__(self, root: tk.Tk, vars_dict: dict, state_vars: dict,
                 set_button_interface: callable, download_button: tk.Button,
                 pb_canvas: tk.Canvas, download_state_ref: any):
        self.root = root
        self.vars = vars_dict
        self.state = state_vars
        self.pb_canvas = pb_canvas
        self.set_button_idle = set_button_interface
        self.download_button = download_button
        self.download_state_ref = download_state_ref
        self.progress_var = tk.DoubleVar(value=0)

    def redraw_bar(self):
        self.pb_canvas.delete("all")
        w = self.pb_canvas.winfo_width()
        h = self.pb_canvas.winfo_height()
        percentage = self.progress_var.get() / 100
        self.pb_canvas.create_rectangle(0, 0, w, h, fill= self.vars['colors']['bg'][0], outline="")
        if 0 < percentage < 1:
            self.pb_canvas.create_rectangle(0, 0, int(w * percentage), h, fill= self.vars['colors']['accent'][0], outline="")

    def _gui_progress_hook(self, d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            percentage = (downloaded / total * 100) if total else 0
            self.root.after(0, self.redraw_bar,)                                                 
            self.root.after(0, self.progress_var.set, percentage)
            self.root.after(0, self.vars['status'].set, "Downloading...")
            self.root.after(0, self.vars['speed'].set, f"{speed/1024/1024:.1f} MB/s" if speed else "")
            self.root.after(0, self.vars['eta'].set, f"ETA {eta}s" if eta else "")
        elif status == "finished":
            self.root.after(0, self.vars['status'].set, "Converting...")
            self.root.after(0, self.vars['speed'].set, "")
            self.root.after(0, self.vars['eta'].set, "")
        elif status == "error":
            self.root.after(0, self.vars['status'].set, "Error during download")

    def _build_output_file(self, output_dir: str):
        stem = self.vars['filename'].get().strip()
        if stem:
            return os.path.join(os.path.expanduser(output_dir), f"{stem}.%(ext)s")
        return os.path.join(os.path.expanduser(output_dir), "%(title)s.%(ext)s")

    def _set_button_downloading(self):
        self.download_state_ref.state = ButtonState.DOWNLOADING
        self.download_button.config(text="Downloading...", state="disabled")

    def do_download(self):
        url = self.vars['url'].get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL first.")
            return

        self.root.after(0, self._set_button_downloading)
        self.progress_var.set(0)
        self.vars['status'].set("Starting...")
        self.vars['speed'].set("")
        self.vars['eta'].set("")

        def worker():
            try:
                check_dependencies(raise_on_missing=True)
                opts = build_ydl_opts(
                    self.vars['output'].get() or "~/Downloads/audio",
                    self.vars['fmt'].get(),
                    self.vars['quality'].get(),
                    self.vars['no_playlist'].get(),
                    progress_hook=self._gui_progress_hook,
                )
                opts["outtmpl"] = self._build_output_file(self.vars['output'].int_path_helper() if hasattr(self.vars['output'], 'int_path_helper') else self.vars['output'].get() or "~/Downloads/audio")

                output_path = self.vars['output'].get() or "~/Downloads/audio"
                opts["outtmpl"] = self._build_output_file(output_path)

                run_download(url, opts)

                self.root.after(0, self.progress_var.set, 100)
                self.root.after(0, self.vars['status'].set, "Done!")

                def _reset_filename():
                    self.state['filename_edited'][0] = False
                    self.state['fn_trace_paused'][0] = True
                    self.vars['filename'].set("")
                    self.state['fn_trace_paused'][0] = False

                self.root.after(0, _reset_filename)
                self.root.after(0, self.vars['speed'].set, "")
                self.root.after(0, self.vars['eta'].set, "")
            except Exception as e:
                self.root.after(0, self.vars['status'].set, f"Error: {e}")
            finally:
                self.root.after(0, self.set_button_idle)

        threading.Thread(target=worker, daemon=True).start()