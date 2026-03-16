#!/usr/bin/env python3
"""
extract_audio.py — Download audio at the highest possible quality from any URL.

Supports: YouTube, SoundCloud, Bandcamp, Vimeo, Twitter/X, Reddit, TikTok,
          Facebook, Instagram, and 1000+ other sites via yt-dlp.

Requirements:
    pip install yt-dlp
    # ffmpeg must also be installed:
    #   macOS:   brew install ffmpeg
    #   Ubuntu:  sudo apt install ffmpeg
    #   Windows: https://ffmpeg.org/download.html

Usage (headless / CLI):
    python extract_audio.py <url> [options]

Usage (GUI):
    python extract_audio.py --ui
    python extract_audio.py          # no args also opens GUI

Examples:
    python extract_audio.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    python extract_audio.py "https://soundcloud.com/artist/track" --format mp3
    python extract_audio.py "https://..." --output ~/Music --format flac
    python extract_audio.py --ui
"""

import argparse
import sys
import os
import shutil
import threading
from dotenv import load_dotenv

load_dotenv()


import json, pathlib

_CONFIG_PATH = pathlib.Path(os.getenv("XDG_CONFIG_HOME",
               os.path.expanduser("~/.config"))) / "audio_extractor" / "settings.json"

_DEFAULTS = {
    "bg":        "#000000",
    "surface":   "#0e0e0e",
    "surface2":  "#141414",
    "border":    "#2a2a30",
    "accent":    "#fffb1b",
    "accent2":   "#5a7ff0",
    "fg":        "#ffffff",
    "fg_dim":    "#7a7a88",
    "font_size": 11,
    "output_dir": "~/Downloads/audio",
    "fmt":       "best",
}

def load_config():
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text())
            return {**_DEFAULTS, **data}
    except Exception:
        pass
    return dict(_DEFAULTS)

def save_config(cfg: dict):
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as e:
        print(f"[config] save failed: {e}")


def check_dependencies(raise_on_missing=False):
    missing = []
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        missing.append("yt-dlp  ->  pip install yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg  ->  brew install ffmpeg  /  sudo apt install ffmpeg")
    if missing:
        msg = "Missing dependencies:\n" + "\n".join(f"  * {m}" for m in missing)
        if raise_on_missing:
            raise RuntimeError(msg)
        print("ERROR  " + msg)
        sys.exit(1)


FORMAT_CODEC_MAP = {
    "best":   None,
    "flac":   "flac",
    "wav":    "pcm_s16le",
    "mp3":    "libmp3lame",
    "aac":    "aac",
    "opus":   "libopus",
    "m4a":    "aac",
    "vorbis": "libvorbis",
}


def build_ydl_opts(output_dir, fmt, quality, no_playlist,
                   progress_hook=None):
    output_dir = os.path.expanduser(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    # "bestaudio" without fallback avoids accidentally picking a muxed stream.
    # For lossless/transcode formats we just need the raw audio bytes; ffmpeg
    # handles the actual encode via FFmpegExtractAudio.
    audio_format = "bestaudio"

    post_processors = []
    if fmt != "best":
        post_processors.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": fmt if fmt != "vorbis" else "vorbis",
            "preferredquality": quality,
        })
    post_processors.append({"key": "FFmpegMetadata"})
    # EmbedThumbnail only works reliably with mp3/m4a/mp4 containers
    embed_thumb_fmts = {"mp3", "m4a", "aac", "best"}
    if fmt in embed_thumb_fmts:
        post_processors.append({"key": "EmbedThumbnail"})

    opts = {
        "format":           audio_format,
        "outtmpl":          os.path.join(output_dir, "%(artist,uploader)s - %(title)s.%(ext)s"),
        "postprocessors":   post_processors,
        "writethumbnail":   fmt in embed_thumb_fmts,
        "embedthumbnail":   fmt in embed_thumb_fmts,
        "addmetadata":      True,
        "progress_hooks":   [progress_hook] if progress_hook else [],
        "noplaylist":       no_playlist,
        "ignoreerrors":     False,
        "quiet":            True,
        "no_warnings":      True,
        "verbose":          False,
        "retries":          5,
        "fragment_retries": 5,
        "sleep_interval":   1,
        "max_sleep_interval": 3,
    }
    return opts


def fetch_info(url, ydl_opts):
    import yt_dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


def run_download(url, ydl_opts):
    import yt_dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def _draw_thumb_placeholder(canvas, w, h, fg, bg):
    canvas.delete("all")
    canvas.create_rectangle(0, 0, w, h, fill=bg, outline="")
    cx, cy = w // 2, h // 2
    canvas.create_oval(cx-14, cy+6,  cx-2,  cy+18, fill=fg, outline="")
    canvas.create_oval(cx+4,  cy-4,  cx+16, cy+8,  fill=fg, outline="")
    canvas.create_line(cx-2,  cy+12, cx-2,  cy-16, fill=fg, width=2)
    canvas.create_line(cx+16, cy+2,  cx+16, cy-22, fill=fg, width=2)
    canvas.create_line(cx-2,  cy-16, cx+16, cy-22, fill=fg, width=2)


def _safe_stem(name):
    import re
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip().rstrip(".")[:180]


# =============================================================================
# CLI MODE
# =============================================================================

def cli_progress_hook(d):
    status = d.get("status")
    if status == "downloading":
        total      = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        downloaded = d.get("downloaded_bytes", 0)
        speed      = d.get("speed") or 0
        eta        = d.get("eta") or 0
        pct        = (downloaded / total * 100) if total else 0
        bar_len    = 30
        filled     = int(bar_len * pct / 100)
        bar        = "#" * filled + "-" * (bar_len - filled)
        speed_s    = f"{speed/1024/1024:.1f} MB/s" if speed else "?"
        eta_s      = f"{eta}s" if eta else "?"
        print(f"\r  [{bar}] {pct:5.1f}%  {speed_s}  ETA {eta_s}   ", end="", flush=True)
    elif status == "finished":
        print(f"\r  Done — converting...{' '*30}")
    elif status == "error":
        print("\n  Download error")


def run_headless(url, output_dir, fmt, quality, no_playlist):
    import yt_dlp
    check_dependencies()
    opts = build_ydl_opts(output_dir, fmt, quality, no_playlist,
                          progress_hook=cli_progress_hook)
    print(f"\nExtracting audio")
    print(f"   URL    : {url}")
    print(f"   Format : {fmt.upper() if fmt != 'best' else 'Best native'}")
    print(f"   Output : {os.path.expanduser(output_dir)}\n")
    try:
        info     = fetch_info(url, opts)
        title    = info.get("title", "Unknown")
        uploader = (info.get("artist") or info.get("uploader")
                    or info.get("channel") or "Unknown artist")
        duration = info.get("duration")
        dur_str  = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "?"
        print(f"   Title  : {title}")
        print(f"   Artist : {uploader}")
        print(f"   Length : {dur_str}\n")
        run_download(url, opts)
        print("\nDone!\n")
    except yt_dlp.utils.DownloadError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


# =============================================================================
# GUI MODE
# =============================================================================

def run_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        print("Tkinter is not available.")
        sys.exit(1)

    _cfg      = load_config()
    BG        = _cfg["bg"]
    SURFACE   = _cfg["surface"]
    SURFACE2  = _cfg["surface2"]
    BORDER    = _cfg["border"]
    ACCENT    = _cfg["accent"]
    ACCENT2   = _cfg["accent2"]
    FG        = _cfg["fg"]
    FG_DIM    = _cfg["fg_dim"]

    root = tk.Tk()
    root.title("Audio Extractor")
    root.configure(bg=BG)
    root.minsize(660, 400)
    _always_on_top = [False]

    if sys.platform.startswith("linux"):
        # Use Tk's built-in splash type — tells the WM to hide decorations
        # while still managing the window normally (stacking, focus, etc.)
        try:
            root.wm_attributes("-type", "splash")
        except Exception:
            root.overrideredirect(True)
    else:
        root.overrideredirect(True)

    # ── Custom titlebar ───────────────────────────────────────────────────────
    _drag = {"x": 0, "y": 0, "dragging": False}

    titlebar = tk.Frame(root, bg=BG, height=36)
    titlebar.pack(fill="x", side="top")
    titlebar.pack_propagate(False)

    title_font = ("Segoe UI", 10, "bold") if sys.platform != "darwin"                  else ("SF Pro Display", 12, "bold")
    tk.Label(titlebar, text="🎵  Audio Extractor",
             bg=BG, fg=ACCENT, font=title_font).pack(side="left", padx=14)

    def _close():    root.destroy()
    def _minimise():
        # overrideredirect windows can't iconify on Linux directly;
        # withdraw is the simplest cross-platform workaround
        root.withdraw()
        # Restore on clicking taskbar / after 0ms (user must reopen via tray/taskbar)
        # For now just re-show after withdraw so it's not lost forever
        root.after(200, root.deiconify)

    btn_close = tk.Button(titlebar, text="✕", command=_close,
                          bg=BG, fg=FG_DIM, font=("Segoe UI", 11),
                          relief="flat", cursor="hand2", padx=10, pady=4,
                          activebackground="#ff5a5a", activeforeground="#fff",
                          bd=0, highlightthickness=0)
    btn_close.pack(side="right")
    btn_min = tk.Button(titlebar, text="−", command=_minimise,
                        bg=BG, fg=FG_DIM, font=("Segoe UI", 13),
                        relief="flat", cursor="hand2", padx=10, pady=4,
                        activebackground=BORDER, activeforeground=FG,
                        bd=0, highlightthickness=0)
    btn_min.pack(side="right")

    def _toggle_ontop():
        _always_on_top[0] = not _always_on_top[0]
        root.wm_attributes("-topmost", _always_on_top[0])
        btn_top.config(fg=ACCENT if _always_on_top[0] else FG_DIM)
    btn_top = tk.Button(titlebar, text="⊤", command=_toggle_ontop,
                        bg=BG, fg=FG_DIM,   # off by default
                        font=("Segoe UI", 11),
                        relief="flat", cursor="hand2", padx=10, pady=4,
                        activebackground=BORDER, activeforeground=FG,
                        bd=0, highlightthickness=0)
    btn_top.pack(side="right")
    # don't set topmost by default — let WM manage stacking

    # Ensure system dialogs (messagebox, filedialog) appear above the window
    def _show_dialog(fn, *a, **kw):
        root.wm_attributes("-topmost", False)
        try:
            return fn(*a, **kw)
        finally:
            root.wm_attributes("-topmost", _always_on_top[0])

    # Drag to move — only drag if mouse actually moves (avoids accidental moves)
    def _tb_press(e):
        _drag["x"] = e.x_root - root.winfo_x()
        _drag["y"] = e.y_root - root.winfo_y()
        _drag["dragging"] = False
    def _tb_drag(e):
        _drag["dragging"] = True
        root.geometry(f"+{e.x_root - _drag['x']}+{e.y_root - _drag['y']}")

    titlebar.bind("<ButtonPress-1>", _tb_press)
    titlebar.bind("<B1-Motion>",     _tb_drag)

    # All-edges resize — bind 8-direction handles on the window border
    _rsz = {"x": 0, "y": 0, "w": 0, "h": 0, "wx": 0, "wy": 0, "edge": ""}
    EDGE = 6   # px from edge that counts as resize zone

    def _edge_cursor(ex, ey, w, h):
        l = ex < EDGE; r = ex > w - EDGE
        t = ey < EDGE; b = ey > h - EDGE
        if t and l: return "top_left_corner",     "nw"
        if t and r: return "top_right_corner",    "ne"
        if b and l: return "bottom_left_corner",  "sw"
        if b and r: return "bottom_right_corner", "se"
        if t:       return "top_side",            "n"
        if b:       return "bottom_side",         "s"
        if l:       return "left_side",           "w"
        if r:       return "right_side",          "e"
        return None, ""

    def _win_motion(e):
        cur, _ = _edge_cursor(e.x, e.y, root.winfo_width(), root.winfo_height())
        if cur:
            root.config(cursor=cur)
        else:
            root.config(cursor="")

    def _win_press(e):
        cur, edge = _edge_cursor(e.x, e.y, root.winfo_width(), root.winfo_height())
        _rsz["edge"] = edge
        _rsz["x"]  = e.x_root; _rsz["y"]  = e.y_root
        _rsz["w"]  = root.winfo_width()
        _rsz["h"]  = root.winfo_height()
        _rsz["wx"] = root.winfo_x()
        _rsz["wy"] = root.winfo_y()

    def _win_resize(e):
        if not _rsz["edge"]:
            return
        dx = e.x_root - _rsz["x"]
        dy = e.y_root - _rsz["y"]
        x, y = _rsz["wx"], _rsz["wy"]
        w, h = _rsz["w"],  _rsz["h"]
        edge = _rsz["edge"]
        # horizontal
        if "e" in edge: w = max(660, w + dx)
        if "w" in edge: nw = max(660, w - dx); x += w - nw; w = nw
        # vertical
        if "s" in edge: h = max(400, h + dy)
        if "n" in edge: nh = max(400, h - dy); y += h - nh; h = nh
        root.geometry(f"{w}x{h}+{x}+{y}")

    root.bind("<Motion>",         _win_motion)
    root.bind("<ButtonPress-1>",  _win_press)
    root.bind("<B1-Motion>",      _win_resize)

    # thin border
    root.config(highlightthickness=1, highlightbackground=BORDER)

    # Fonts must be created after the root window exists
    _face      = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"
    _face_mono = "SF Mono"        if sys.platform == "darwin" else "Consolas"
    _base      = _cfg.get("font_size", 13 if sys.platform == "darwin" else 11)

    import tkinter.font as tkFont
    FONT_UI   = tkFont.Font(family=_face,      size=_base)
    FONT_SM   = tkFont.Font(family=_face,      size=_base - 2)
    FONT_MONO = tkFont.Font(family=_face_mono, size=_base - 2)
    FONT_BIG  = tkFont.Font(family=_face,      size=_base + 9, weight="bold")

    THUMB_W, THUMB_H = 120, 120

    url_var          = tk.StringVar()
    fmt_var          = tk.StringVar(value=os.getenv("FORMAT", _cfg.get("fmt", "best")))
    quality_var      = tk.StringVar(value="0")
    output_var       = tk.StringVar(value=os.path.expanduser(
                           os.getenv("OUTPUT_FOLDER", _cfg.get("output_dir", "~/Downloads/audio"))))
    no_playlist      = tk.BooleanVar(value=True)
    filename_var     = tk.StringVar()
    filename_edited  = [False]
    progress_var     = tk.DoubleVar(value=0)
    status_var       = tk.StringVar(value="Ready")
    speed_var        = tk.StringVar(value="")
    eta_var          = tk.StringVar(value="")
    meta_title_var   = tk.StringVar(value="")
    meta_artist_var  = tk.StringVar(value="")
    meta_dur_var     = tk.StringVar(value="")
    meta_src_var     = tk.StringVar(value="")
    _thumb_ref       = [None]
    _info_visible    = [False]

    def frame(parent, **kw):
        return tk.Frame(parent, bg=kw.pop("bg", BG), **kw)

    def label(parent, text="", fg=FG, font=FONT_UI, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=kw.pop("bg", BG), font=font, **kw)

    def entry(parent, textvariable=None, width=40, **kw):
        e = tk.Entry(parent, textvariable=textvariable, width=width,
                     bg=SURFACE, fg=FG, insertbackground=ACCENT,
                     relief="flat", font=FONT_MONO,
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT, **kw)
        # Ctrl+A select-all (not bound by default on Linux)
        e.bind("<Control-a>", lambda e: (e.widget.select_range(0, "end"),
                                         e.widget.icursor("end"), "break"))
        return e

    def accent_btn(parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=ACCENT, fg="#0d0d0f",
                         font=tkFont.Font(family=_face, size=_base, weight="bold"),
                         relief="flat", cursor="hand2",
                         activebackground=ACCENT2, activeforeground="#0d0d0f",
                         padx=18, pady=8, **kw)

    def ghost_btn(parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=SURFACE, fg=FG_DIM, font=FONT_SM,
                         relief="flat", cursor="hand2",
                         activebackground=BORDER, activeforeground=FG,
                         padx=10, pady=5,
                         highlightthickness=1, highlightbackground=BORDER, **kw)

    def seg_btn(parent, text, command):
        return tk.Button(parent, text=text, command=command,
                         bg=SURFACE2, fg=FG_DIM, font=FONT_SM,
                         relief="flat", cursor="hand2",
                         padx=10, pady=4,
                         highlightthickness=1, highlightbackground=BORDER)

    def divider(parent):
        return tk.Frame(parent, bg=BORDER, height=1)

    class ToggleButton(tk.Frame):
        """A pill-shaped on/off toggle that matches the app aesthetic."""
        W, H, R = 44, 24, 12   # width, height, corner radius

        def __init__(self, parent, variable, **kw):
            super().__init__(parent, bg=kw.pop("bg", BG), cursor="hand2")
            self._var = variable
            self._canvas = tk.Canvas(self, width=self.W, height=self.H,
                                     bg=kw.pop("canvasbg", BG),
                                     highlightthickness=0, bd=0)
            self._canvas.pack()
            self._canvas.bind("<Button-1>", self._toggle)
            self._var.trace_add("write", lambda *_: self._draw())
            self._draw()

        def _toggle(self, _=None):
            self._var.set(not self._var.get())

        def _draw(self):
            c = self._canvas
            c.delete("all")
            on  = self._var.get()
            track = ACCENT if on else BORDER
            knob  = "#0d0d0f" if on else FG_DIM
            kx    = self.W - self.R - 4 if on else self.R + 4
            # track
            c.create_oval(0, 0, self.H, self.H, fill=track, outline="")
            c.create_oval(self.W-self.H, 0, self.W, self.H, fill=track, outline="")
            c.create_rectangle(self.H//2, 0, self.W-self.H//2, self.H,
                               fill=track, outline="")
            # knob
            c.create_oval(kx-self.R+4, 4, kx+self.R-4, self.H-4,
                          fill=knob, outline="")

    # ── Notebook (tabs) ──────────────────────────────────────────────────────
    style = ttk.Style()
    style.theme_use("default")
    style.configure("App.TNotebook",
                    background=BG, borderwidth=0, tabmargins=0)
    style.configure("App.TNotebook.Tab",
                    background=SURFACE2, foreground=FG_DIM,
                    font=(_face, _base - 1),
                    padding=(16, 6), borderwidth=0)
    style.map("App.TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACCENT)])

    nb = ttk.Notebook(root, style="App.TNotebook")
    nb.pack(fill="both", expand=True)

    # Tab frames
    tab_dl  = frame(nb, bg=BG)
    tab_cfg = frame(nb, bg=BG)
    nb.add(tab_dl,  text="  Download  ")
    nb.add(tab_cfg, text="  Settings  ")

    # ── Download tab header ───────────────────────────────────────────────────
    hdr = frame(tab_dl)
    hdr.pack(fill="x", padx=24, pady=(20, 4))
    label(hdr, "Audio Extractor", font=FONT_BIG, fg=ACCENT).pack(side="left")
    label(hdr, "yt-dlp powered", fg=FG_DIM, font=FONT_SM).pack(side="left", padx=12, pady=(8, 0))
    divider(tab_dl).pack(fill="x", padx=24, pady=8)

    # URL
    url_row = frame(tab_dl)
    url_row.pack(fill="x", padx=24, pady=(4, 2))
    label(url_row, "URL", fg=FG_DIM, font=FONT_SM, width=9, anchor="w").pack(side="left", padx=(0, 8))
    entry(url_row, textvariable=url_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    ghost_btn(url_row, "✕", lambda: url_var.set("")).pack(side="left", padx=(0, 8))

    def _on_url_changed(*_):
        # Reset filename field so next fetch auto-fills it fresh
        filename_edited[0] = False
        _fn_trace_paused[0] = True
        filename_var.set("")
        _fn_trace_paused[0] = False
    url_var.trace_add("write", _on_url_changed)

    # Output dir
    out_row = frame(tab_dl)
    out_row.pack(fill="x", padx=24, pady=2)
    label(out_row, "Output dir", fg=FG_DIM, font=FONT_SM, width=9, anchor="w").pack(side="left", padx=(0, 8))
    entry(out_row, textvariable=output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    def browse_dir():
        d = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if d:
            output_var.set(d)
    ghost_btn(out_row, "Browse...", browse_dir).pack(side="left")

    # Filename
    fn_row = frame(tab_dl)
    fn_row.pack(fill="x", padx=24, pady=2)
    label(fn_row, "Filename", fg=FG_DIM, font=FONT_SM, width=9, anchor="w").pack(side="left", padx=(0, 8))
    fn_entry = entry(fn_row, textvariable=filename_var)
    fn_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    def _clear_filename():
        filename_edited[0] = False
        _fn_trace_paused[0] = True
        filename_var.set("")
        _fn_trace_paused[0] = False
    ghost_btn(fn_row, "✕", _clear_filename).pack(side="left", padx=(0, 8))
    label(fn_row, "(auto-filled after fetch; edit to override)", fg=FG_DIM, font=FONT_SM).pack(side="left")
    def _on_filename_changed(*_):
        # Only mark as edited if the user actually typed something,
        # not when we programmatically set it (we temporarily pause the trace)
        if not _fn_trace_paused[0]:
            filename_edited[0] = True
    _fn_trace_paused = [False]
    filename_var.trace_add("write", _on_filename_changed)

    # Format segmented control
    fmt_row = frame(tab_dl)
    fmt_row.pack(fill="x", padx=24, pady=(6, 2))
    label(fmt_row, "Format", fg=FG_DIM, font=FONT_SM, width=9, anchor="w").pack(side="left", padx=(0, 8))
    fmt_seg = frame(fmt_row)
    fmt_seg.pack(side="left")
    _fmt_btns = {}

    def _select_fmt(f):
        fmt_var.set(f)
        for name, btn in _fmt_btns.items():
            if name == f:
                btn.config(bg=ACCENT, fg="#0d0d0f", highlightbackground=ACCENT)
            else:
                btn.config(bg=SURFACE2, fg=FG_DIM, highlightbackground=BORDER)

    for i, fmt_name in enumerate(FORMAT_CODEC_MAP):
        b = seg_btn(fmt_seg, fmt_name.upper(), lambda f=fmt_name: _select_fmt(f))
        b.grid(row=0, column=i, padx=(0, 2))
        _fmt_btns[fmt_name] = b
    _select_fmt(fmt_var.get())

    label(fmt_row, "  Q", fg=FG_DIM, font=FONT_SM).pack(side="left", padx=(12, 4))
    entry(fmt_row, textvariable=quality_var, width=5).pack(side="left")
    label(fmt_row, "(mp3: 0=best...9  |  aac/opus: kbps)", fg=FG_DIM, font=FONT_SM).pack(side="left", padx=8)

    pl_row = frame(tab_dl)
    pl_row.pack(fill="x", padx=24, pady=(6, 4))
    label(pl_row, "", width=9).pack(side="left")
    ToggleButton(pl_row, variable=no_playlist).pack(side="left", padx=(0, 10))
    label(pl_row, "Single track only (skip playlist)", fg=FG_DIM, font=FONT_SM).pack(side="left")

    divider(tab_dl).pack(fill="x", padx=24, pady=(8, 0))

    # Info card (hidden until fetch)
    info_card = frame(tab_dl, bg=SURFACE)
    info_outer = frame(info_card, bg=SURFACE)
    info_outer.pack(fill="x", padx=12, pady=10)

    thumb_canvas = tk.Canvas(info_outer, width=THUMB_W, height=THUMB_H,
                             bg=SURFACE2, highlightthickness=1,
                             highlightbackground=BORDER)
    thumb_canvas.pack(side="left", padx=(4, 16))
    _draw_thumb_placeholder(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2)

    meta_inner = frame(info_outer, bg=SURFACE)
    meta_inner.pack(side="left", fill="both", expand=True)

    def _meta_row(parent, key, var, fg_val=FG):
        r = frame(parent, bg=SURFACE)
        r.pack(fill="x", pady=2)
        label(r, key, fg=FG_DIM, font=FONT_SM, width=8, anchor="w", bg=SURFACE).pack(side="left")
        label(r, textvariable=var, fg=fg_val, font=FONT_SM, anchor="w", bg=SURFACE).pack(side="left")

    _meta_row(meta_inner, "Title",  meta_title_var)
    _meta_row(meta_inner, "Artist", meta_artist_var)
    dur_src = frame(meta_inner, bg=SURFACE)
    dur_src.pack(fill="x", pady=2)
    label(dur_src, "Length", fg=FG_DIM, font=FONT_SM, width=8, anchor="w", bg=SURFACE).pack(side="left")
    label(dur_src, textvariable=meta_dur_var, fg=FG, font=FONT_SM, bg=SURFACE).pack(side="left")
    label(dur_src, "  Source", fg=FG_DIM, font=FONT_SM, bg=SURFACE).pack(side="left", padx=(16, 4))
    label(dur_src, textvariable=meta_src_var, fg=ACCENT2, font=FONT_SM, bg=SURFACE).pack(side="left")

    def _show_info_card():
        if not _info_visible[0]:
            # Insert the card just before the progress bar so it appears
            # after the playlist checkbox and divider
            info_card.pack(fill="x", padx=24, pady=(4, 4), before=pb_frame)
            _info_visible[0] = True

    # Progress bar
    pb_frame = frame(tab_dl)
    pb_frame.pack(fill="x", padx=24, pady=(8, 2))
    pb_canvas = tk.Canvas(pb_frame, bg=SURFACE, height=6,
                          highlightthickness=0, relief="flat")
    pb_canvas.pack(fill="x")
    pb_canvas.bind("<Configure>", lambda e: _redraw_bar())

    def _redraw_bar():
        pb_canvas.delete("all")
        w = pb_canvas.winfo_width()
        h = pb_canvas.winfo_height()
        pct = progress_var.get() / 100
        pb_canvas.create_rectangle(0, 0, w, h, fill=BORDER, outline="")
        if pct > 0:
            pb_canvas.create_rectangle(0, 0, int(w * pct), h, fill=ACCENT, outline="")

    def update_progress_bar(pct):
        progress_var.set(pct)
        _redraw_bar()

    st_row = frame(tab_dl)
    st_row.pack(fill="x", padx=24, pady=(2, 0))
    label(st_row, textvariable=status_var, fg=FG_DIM, font=FONT_SM).pack(side="left")
    label(st_row, textvariable=speed_var,  fg=ACCENT,  font=FONT_SM).pack(side="left", padx=12)
    label(st_row, textvariable=eta_var,    fg=FG_DIM,  font=FONT_SM).pack(side="left")

    btn_row = frame(tab_dl)
    btn_row.pack(fill="x", padx=24, pady=(14, 20))
    dl_btn   = accent_btn(btn_row, "Download", lambda: None)
    dl_btn.pack(side="left")
    info_btn = ghost_btn(btn_row, "Fetch Info", lambda: None)
    info_btn.pack(side="left", padx=12)

    # Thumbnail loading
    def _load_thumbnail(urls):
        import io
        if isinstance(urls, str):
            urls = [urls]
        from PIL import Image, ImageTk
        import urllib.request

        img = None
        for url_or_path in urls:
            try:
                if url_or_path.startswith("http"):
                    try:
                        import requests
                        r = requests.get(url_or_path, timeout=10,
                                         headers={"User-Agent": "Mozilla/5.0"})
                        r.raise_for_status()
                        data = r.content
                    except Exception:
                        req = urllib.request.Request(
                            url_or_path, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=10) as r:
                            data = r.read()
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                else:
                    img = Image.open(url_or_path).convert("RGB")
                break
            except Exception as e:
                print(f"[thumb] skipping {url_or_path[:60]}: {e}")
                continue

        if img is None:
            root.after(0, lambda: _draw_thumb_placeholder(
                thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2))
            return

        try:
            img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
            bg_color = tuple(int(SURFACE2[i:i+2], 16) for i in (1, 3, 5))
            bg = Image.new("RGB", (THUMB_W, THUMB_H), bg_color)
            ox = (THUMB_W - img.width) // 2
            oy = (THUMB_H - img.height) // 2
            bg.paste(img, (ox, oy))

            def _paint(pil_img=bg):
                try:
                    photo = ImageTk.PhotoImage(pil_img)
                    _thumb_ref[0] = photo
                    thumb_canvas.delete("all")
                    thumb_canvas.create_image(0, 0, anchor="nw", image=photo)
                    thumb_canvas.update_idletasks()
                except Exception as e:
                    print(f"[thumb _paint error] {e}")

            root.after(0, _paint)
        except Exception as e:
            print(f"[thumb process error] {e}")
            root.after(0, lambda: _draw_thumb_placeholder(
                thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2))

    def _set_thumbnail(urls):
        if isinstance(urls, str):
            urls = [urls]
        threading.Thread(target=_load_thumbnail, args=(urls,), daemon=True).start()

    def _clear_thumbnail():
        thumb_canvas.delete("all")
        _draw_thumb_placeholder(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2)
        _thumb_ref[0] = None

    def _build_outtmpl(output_dir):
        stem = filename_var.get().strip()
        if stem:
            return os.path.join(os.path.expanduser(output_dir), f"{stem}.%(ext)s")
        return os.path.join(os.path.expanduser(output_dir),
                            "%(title)s.%(ext)s")

    def gui_progress_hook(d):
        status = d.get("status")
        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed      = d.get("speed") or 0
            eta        = d.get("eta") or 0
            pct        = (downloaded / total * 100) if total else 0
            root.after(0, update_progress_bar, pct)
            root.after(0, status_var.set, "Downloading...")
            root.after(0, speed_var.set, f"{speed/1024/1024:.1f} MB/s" if speed else "")
            root.after(0, eta_var.set,   f"ETA {eta}s" if eta else "")
        elif status == "finished":
            root.after(0, status_var.set, "Converting...")
            root.after(0, speed_var.set, "")
            root.after(0, eta_var.set,   "")
        elif status == "error":
            root.after(0, status_var.set, "Error during download")

    def do_fetch_info():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL first.")
            return
        status_var.set("Fetching info...")
        meta_title_var.set("...")
        meta_artist_var.set("")
        meta_dur_var.set("")
        meta_src_var.set("")
        root.after(0, _clear_thumbnail)
        root.after(0, _show_info_card)

        def worker():
            try:
                check_dependencies(raise_on_missing=True)
                opts = build_ydl_opts(
                    output_var.get() or "~/Downloads/audio",
                    fmt_var.get(), quality_var.get(),
                    no_playlist.get(),
                )
                info     = fetch_info(url, opts)
                title    = info.get("title", "Unknown")
                artist   = (info.get("artist") or info.get("uploader")
                            or info.get("channel") or "Unknown")
                duration = info.get("duration")
                dur_s    = (f"{int(duration)//60}:{int(duration)%60:02d}"
                            if duration else "?")
                acodec   = info.get("acodec", "?")
                abr      = info.get("abr", "?")

                thumbnails = info.get("thumbnails") or []
                def _thumb_score(t):
                    w = t.get("width") or 0
                    h = t.get("height") or 0
                    penalty = -1 if str(t.get("url", "")).endswith(".webp") else 0
                    return (w * h) + penalty
                ordered = sorted([t for t in thumbnails if t.get("url")],
                                  key=_thumb_score, reverse=True)
                thumb_urls = [t["url"] for t in ordered]
                if not thumb_urls and info.get("thumbnail"):
                    thumb_urls = [info["thumbnail"]]

                root.after(0, meta_title_var.set,  title)
                root.after(0, meta_artist_var.set, artist)
                root.after(0, meta_dur_var.set,    dur_s)
                root.after(0, meta_src_var.set,    f"{acodec} @ {abr} kbps")
                root.after(0, status_var.set, "Info fetched - ready to download")

                def _set_filename(a=artist, t=title):
                    _fn_trace_paused[0] = True
                    filename_var.set(_safe_stem(f"{t}"))
                    _fn_trace_paused[0] = False
                if not filename_edited[0]:
                    root.after(0, _set_filename)
                if thumb_urls:
                    _set_thumbnail(thumb_urls)
            except Exception as e:
                root.after(0, status_var.set, f"Error: {e}")
                root.after(0, meta_title_var.set, "-")

        threading.Thread(target=worker, daemon=True).start()

    def do_download():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL first.")
            return
        dl_btn.config(state="disabled", text="Downloading...")
        info_btn.config(state="disabled")
        update_progress_bar(0)
        status_var.set("Starting...")
        speed_var.set("")
        eta_var.set("")

        def worker():
            try:
                check_dependencies(raise_on_missing=True)
                opts = build_ydl_opts(
                    output_var.get() or "~/Downloads/audio",
                    fmt_var.get(), quality_var.get(),
                    no_playlist.get(),
                    progress_hook=gui_progress_hook,
                )
                opts["outtmpl"] = _build_outtmpl(output_var.get() or "~/Downloads/audio")
                run_download(url, opts)
                root.after(0, update_progress_bar, 100)
                root.after(0, status_var.set, "Done!")
                def _reset_filename():
                    filename_edited[0] = False
                    _fn_trace_paused[0] = True
                    filename_var.set("")
                    _fn_trace_paused[0] = False
                root.after(0, _reset_filename)
                root.after(0, speed_var.set, "")
                root.after(0, eta_var.set,   "")
            except Exception as e:
                root.after(0, status_var.set, f"Error: {e}")
            finally:
                root.after(0, dl_btn.config,  {"state": "normal", "text": "Download"})
                root.after(0, info_btn.config, {"state": "normal"})

        threading.Thread(target=worker, daemon=True).start()

    dl_btn.config(command=do_download)
    info_btn.config(command=do_fetch_info)

    # ── Font size slider ──────────────────────────────────────────────────────
    font_row = frame(tab_dl)
    font_row.pack(fill="x", padx=24, pady=(0, 16))

    font_size_var = tk.IntVar(value=_base)

    def _update_fonts(val):
        sz = int(val)
        FONT_UI.configure(size=sz)
        FONT_SM.configure(size=max(sz - 2, 7))
        FONT_MONO.configure(size=max(sz - 2, 7))
        FONT_BIG.configure(size=sz + 9)
        # accent_btn uses a separate Font instance — update all buttons directly
        for btn in [dl_btn]:
            try:
                btn.configure(font=tkFont.Font(family=_face, size=sz, weight="bold"))
            except Exception:
                pass

    # ── Settings tab ─────────────────────────────────────────────────────────
    cfg_hdr = frame(tab_cfg)
    cfg_hdr.pack(fill="x", padx=24, pady=(20, 4))
    label(cfg_hdr, "Settings", font=FONT_BIG, fg=ACCENT).pack(side="left")
    divider(tab_cfg).pack(fill="x", padx=24, pady=8)

    # Mutable colour state (lists so nonlocal isn't needed in nested fns)
    _accent = [ACCENT]
    _bg     = [BG]

    def cfg_row(lbl, widget_fn):
        r = frame(tab_cfg, bg=_bg[0])
        r.pack(fill="x", padx=24, pady=8)
        label(r, lbl, fg=FG_DIM, font=FONT_SM, width=16, anchor="w",
              bg=_bg[0]).pack(side="left", padx=(0, 12))
        widget_fn(r)
        return r

    def _recolor_all():
        """Walk every widget and update bg/fg to match new BG."""
        new_bg = _bg[0]
        def _walk(w):
            cls = w.winfo_class()
            try:
                if cls in ("Frame", "Label", "Checkbutton"):
                    if w.cget("bg") not in (_accent[0], SURFACE, SURFACE2, BORDER):
                        w.config(bg=new_bg)
                elif cls == "Button":
                    if w.cget("bg") not in (_accent[0], SURFACE, SURFACE2):
                        w.config(bg=new_bg)
            except Exception:
                pass
            for child in w.winfo_children():
                _walk(child)
        _walk(root)
        root.config(bg=new_bg)

    # ── Colour section header ─────────────────────────────────────────────────
    label(tab_cfg, "Colours", fg=FG_DIM, font=FONT_SM).pack(
        anchor="w", padx=24, pady=(4, 0))

    # Helper: a clickable colour swatch
    _swatches = {}
    def _make_swatch(parent, key, current_hex, on_pick):
        sw = tk.Frame(parent, bg=current_hex, width=32, height=32,
                      cursor="hand2", highlightthickness=1,
                      highlightbackground=BORDER)
        sw.pack(side="left", padx=(0, 8))
        sw.pack_propagate(False)
        sw.bind("<Button-1>", lambda _: on_pick())
        _swatches[key] = sw
        return sw

    # ── Custom colour picker popup ────────────────────────────────────────────
    def _open_colour_picker(initial_hex, title, on_select):
        """
        Full in-app colour picker:
          - Hue bar across the top
          - SV (saturation/brightness) square
          - Preset palette
          - Hex entry + live preview
        """
        import colorsys

        popup = tk.Toplevel(root)
        popup.title(title)
        popup.configure(bg=SURFACE)
        popup.resizable(False, False)
        popup.transient(root)          # float above root
        popup.wm_attributes("-topmost", True)
        popup.after(50, popup.grab_set)
        popup.after(50, popup.lift)

        PAD   = 16
        SW    = 260   # SV square width/height
        HH    = 18    # hue bar height
        PW    = 16    # preset swatch size

        # parse initial colour
        def hex_to_hsv(h):
            h = h.lstrip("#")
            if len(h) != 6: return (0.0, 1.0, 1.0)
            r, g, b = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
            return colorsys.rgb_to_hsv(r, g, b)

        def hsv_to_hex(h, s, v):
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

        _h, _s, _v = hex_to_hsv(initial_hex)
        state = {"h": _h, "s": _s, "v": _v}

        # ── Hue bar ───────────────────────────────────────────────────────────
        hue_canvas = tk.Canvas(popup, width=SW, height=HH,
                               highlightthickness=0, bd=0)
        hue_canvas.pack(padx=PAD, pady=(PAD, 4))

        def _draw_hue():
            hue_canvas.delete("all")
            for x in range(SW):
                h = x / SW
                r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                col = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
                hue_canvas.create_line(x, 0, x, HH, fill=col)
            # cursor
            cx = int(state["h"] * SW)
            hue_canvas.create_rectangle(cx-2, 0, cx+2, HH,
                                        outline="white", fill="", width=2)

        def _hue_click(e):
            state["h"] = max(0.0, min(1.0, e.x / SW))
            _draw_hue()
            _draw_sv()
            _sync_hex()
        hue_canvas.bind("<Button-1>", _hue_click)
        hue_canvas.bind("<B1-Motion>", _hue_click)

        # ── SV square ─────────────────────────────────────────────────────────
        sv_canvas = tk.Canvas(popup, width=SW, height=SW,
                              highlightthickness=0, bd=0)
        sv_canvas.pack(padx=PAD, pady=4)
        # Cache rendered image to avoid per-pixel slowness
        _sv_img = [None]

        def _draw_sv():
            try:
                from PIL import Image, ImageTk
                img = Image.new("RGB", (SW, SW))
                px  = img.load()
                h   = state["h"]
                for y in range(SW):
                    v = 1.0 - y / SW
                    for x in range(SW):
                        s = x / SW
                        r, g, b = colorsys.hsv_to_rgb(h, s, v)
                        px[x, y] = (int(r*255), int(g*255), int(b*255))
                photo = ImageTk.PhotoImage(img)
                _sv_img[0] = photo
                sv_canvas.create_image(0, 0, anchor="nw", image=photo)
            except ImportError:
                # Pillow not available — fallback: draw column strips
                sv_canvas.delete("all")
                h = state["h"]
                for x in range(0, SW, 2):
                    s = x / SW
                    for y in range(0, SW, 2):
                        v = 1.0 - y / SW
                        r, g, b = colorsys.hsv_to_rgb(h, s, v)
                        col = "#{:02x}{:02x}{:02x}".format(
                            int(r*255), int(g*255), int(b*255))
                        sv_canvas.create_rectangle(x, y, x+2, y+2,
                                                   fill=col, outline="")
            # crosshair
            cx = int(state["s"] * SW)
            cy = int((1.0 - state["v"]) * SW)
            sv_canvas.create_oval(cx-7, cy-7, cx+7, cy+7,
                                  outline="white", width=2)
            sv_canvas.create_oval(cx-5, cy-5, cx+5, cy+5,
                                  outline="black", width=1)

        def _sv_click(e):
            state["s"] = max(0.0, min(1.0, e.x / SW))
            state["v"] = max(0.0, min(1.0, 1.0 - e.y / SW))
            _draw_sv()
            _sync_hex()
        sv_canvas.bind("<Button-1>", _sv_click)
        sv_canvas.bind("<B1-Motion>", _sv_click)

        # ── Preset palette ────────────────────────────────────────────────────
        PRESETS = [
            # greens / limes
            "#20ff10", "#39ff14", "#00ff7f", "#7fff00", "#adff2f",
            # blues / purples
            "#5a7ff0", "#4fc3f7", "#7c4dff", "#e040fb", "#f06292",
            # warm
            "#ff5252", "#ff9800", "#ffd740", "#ffffff", "#aaaaaa",
            # darks
            "#0d0d0f", "#141414", "#1e1e24", "#2a2a30", "#000000",
        ]
        preset_frame = frame(popup, bg=SURFACE)
        preset_frame.pack(padx=PAD, pady=4, anchor="w")
        for i, col in enumerate(PRESETS):
            def _preset_click(c=col):
                h, s, v = hex_to_hsv(c)
                state["h"], state["s"], state["v"] = h, s, v
                _draw_hue()
                _draw_sv()
                _sync_hex()
            sw = tk.Frame(preset_frame, bg=col, width=PW, height=PW,
                          cursor="hand2", highlightthickness=1,
                          highlightbackground="#333")
            sw.grid(row=i//10, column=i%10, padx=1, pady=1)
            sw.pack_propagate(False)
            sw.bind("<Button-1>", lambda _, c=col: _preset_click(c))

        # ── Hex input + preview ───────────────────────────────────────────────
        bottom = frame(popup, bg=SURFACE)
        bottom.pack(fill="x", padx=PAD, pady=(8, PAD))

        preview = tk.Frame(bottom, width=40, height=32, bg=initial_hex,
                           highlightthickness=1, highlightbackground=BORDER)
        preview.pack(side="left", padx=(0, 10))
        preview.pack_propagate(False)

        hex_var = tk.StringVar(value=initial_hex)
        hex_entry = tk.Entry(bottom, textvariable=hex_var, width=10,
                             bg=SURFACE2, fg=FG, insertbackground=ACCENT,
                             relief="flat", font=FONT_MONO,
                             highlightthickness=1, highlightbackground=BORDER)
        hex_entry.pack(side="left", padx=(0, 10))

        def _sync_hex(*_):
            col = hsv_to_hex(state["h"], state["s"], state["v"])
            hex_var.set(col)
            preview.config(bg=col)

        def _hex_typed(*_):
            h = hex_var.get().strip()
            if not h.startswith("#"): h = "#" + h
            if len(h) == 7:
                try:
                    int(h[1:], 16)
                    hs, s, v = hex_to_hsv(h)
                    state["h"], state["s"], state["v"] = hs, s, v
                    _draw_hue(); _draw_sv()
                    preview.config(bg=h)
                except ValueError:
                    pass
        hex_var.trace_add("write", _hex_typed)

        def _confirm():
            col = hsv_to_hex(state["h"], state["s"], state["v"])
            popup.destroy()
            on_select(col)

        accent_btn(bottom, "Apply", _confirm).pack(side="left", padx=(8, 0))

        # initial draw (after window is visible so canvas has size)
        popup.after(50, _draw_hue)
        popup.after(50, _draw_sv)
        _sync_hex()

    # ── Apply helpers ─────────────────────────────────────────────────────────
    toggle_ref = [None]

    _colors = {
        "bg": _bg, "surface": [SURFACE], "surface2": [SURFACE2],
        "border": [BORDER], "accent": _accent, "accent2": [ACCENT2],
        "fg": [FG], "fg_dim": [FG_DIM],
    }

    def _current_cfg():
        return {k: _colors[k][0] for k in _colors} | {
            "font_size":  font_size_var.get(),
            "output_dir": output_var.get(),
            "fmt":        fmt_var.get(),
        }

    def _apply_accent_col(col):
        _accent[0] = col
        _colors["accent"][0] = col
        _swatches["accent"].config(bg=col)
        dl_btn.config(bg=col, activebackground=col)
        for b in list(_fmt_btns.values()):
            if b.cget("bg") not in (SURFACE2, _bg[0], SURFACE):
                b.config(bg=col, highlightbackground=col)
        if toggle_ref[0]:
            toggle_ref[0]._draw()
        _redraw_bar()

    def _apply_bg_col(col):
        _bg[0] = col
        _colors["bg"][0] = col
        _swatches["bg"].config(bg=col)
        _recolor_all()

    # ── Full colour palette ───────────────────────────────────────────────────
    _COLOUR_DEFS = [
        ("accent",   "Accent",     _colors["accent"],   _apply_accent_col),
        ("bg",       "Background", _colors["bg"],       _apply_bg_col),
        ("surface",  "Surface",    _colors["surface"],
         lambda c: [_colors["surface"].__setitem__(0, c), _recolor_all()]),
        ("surface2", "Surface 2",  _colors["surface2"],
         lambda c: [_colors["surface2"].__setitem__(0, c), _recolor_all()]),
        ("border",   "Border",     _colors["border"],
         lambda c: [_colors["border"].__setitem__(0, c), _recolor_all()]),
        ("accent2",  "Accent 2",   _colors["accent2"],
         lambda c: _colors["accent2"].__setitem__(0, c)),
        ("fg",       "Text",       _colors["fg"],
         lambda c: [_colors["fg"].__setitem__(0, c), _recolor_all()]),
        ("fg_dim",   "Text dim",   _colors["fg_dim"],
         lambda c: [_colors["fg_dim"].__setitem__(0, c), _recolor_all()]),
    ]

    pal_frame = frame(tab_cfg)
    pal_frame.pack(fill="x", padx=24, pady=6)
    for i, (key, lbl, ref, apply_fn) in enumerate(_COLOUR_DEFS):
        cell = frame(pal_frame)
        cell.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 40), pady=5)
        _make_swatch(cell, key, ref[0],
                     lambda r=ref, a=apply_fn:
                         _open_colour_picker(r[0], "Pick colour", a))
        label(cell, lbl, fg=FG_DIM, font=FONT_SM).pack(side="left", padx=(8, 0))

    divider(tab_cfg).pack(fill="x", padx=24, pady=(12, 4))

    # ── Font size ─────────────────────────────────────────────────────────────
    label(tab_cfg, "Font size", fg=FG_DIM, font=FONT_SM).pack(
        anchor="w", padx=24, pady=(4, 0))
    font_cfg_row = frame(tab_cfg)
    font_cfg_row.pack(fill="x", padx=24, pady=6)
    def _font_dec2():
        v = max(8, font_size_var.get() - 1); font_size_var.set(v); _update_fonts(v)
    def _font_inc2():
        v = min(24, font_size_var.get() + 1); font_size_var.set(v); _update_fonts(v)
    ghost_btn(font_cfg_row, "−", _font_dec2).pack(side="left")
    label(font_cfg_row, textvariable=font_size_var, fg=FG, font=FONT_SM,
          width=3, anchor="center").pack(side="left", padx=4)
    ghost_btn(font_cfg_row, "+", _font_inc2).pack(side="left")

    divider(tab_cfg).pack(fill="x", padx=24, pady=(12, 4))

    # ── Default output dir ────────────────────────────────────────────────────
    label(tab_cfg, "Default output dir", fg=FG_DIM, font=FONT_SM).pack(
        anchor="w", padx=24, pady=(4, 0))
    outdir_row = frame(tab_cfg)
    outdir_row.pack(fill="x", padx=24, pady=6)
    entry(outdir_row, textvariable=output_var, width=36).pack(side="left", padx=(0, 8))
    def _br2():
        d = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if d: output_var.set(d)
    ghost_btn(outdir_row, "Browse...", _br2).pack(side="left")

    def _find_toggle(w):
        if isinstance(w, ToggleButton):
            toggle_ref[0] = w
            return
        for c in w.winfo_children():
            _find_toggle(c)
    root.after(100, lambda: _find_toggle(root))

    # ── Save / Reset ──────────────────────────────────────────────────────────
    divider(tab_cfg).pack(fill="x", padx=24, pady=(16, 8))
    save_row = frame(tab_cfg)
    save_row.pack(fill="x", padx=24, pady=(0, 20))

    _save_lbl = tk.StringVar(value="Save settings")
    def _save_settings():
        save_config(_current_cfg())
        _save_lbl.set("Saved ✓")
        root.after(1500, lambda: _save_lbl.set("Save settings"))

    save_btn = accent_btn(save_row, "", _save_settings)
    save_btn.config(textvariable=_save_lbl)
    save_btn.pack(side="left")

    def _reset_settings():
        if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
            try:
                _CONFIG_PATH.unlink(missing_ok=True)
            except Exception:
                pass
            messagebox.showinfo("Reset", "Defaults restored — restart to apply.")
    ghost_btn(save_row, "Reset to defaults", _reset_settings).pack(side="left", padx=12)

    # Config file path — clickable, opens parent folder
    def _open_config_dir():
        import subprocess
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        folder = str(_CONFIG_PATH.parent)
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", folder])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["explorer", folder])

    cfg_path_row = frame(tab_cfg)
    cfg_path_row.pack(fill="x", padx=24, pady=(4, 0))
    label(cfg_path_row, "Config", fg=FG_DIM, font=FONT_SM, width=9, anchor="w").pack(side="left", padx=(0, 8))
    path_lbl = tk.Label(cfg_path_row, text=str(_CONFIG_PATH),
                        fg=FG_DIM, bg=BG, font=FONT_SM,
                        cursor="hand2", anchor="w")
    path_lbl.pack(side="left")
    path_lbl.bind("<Enter>", lambda e: path_lbl.config(fg=ACCENT))
    path_lbl.bind("<Leave>", lambda e: path_lbl.config(fg=FG_DIM))
    path_lbl.bind("<Button-1>", lambda e: _open_config_dir())

    root.mainloop()


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download audio at the highest quality from any URL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=True,
    )
    parser.add_argument("url", nargs="?", default=None,
                        help="URL to download (omit to open GUI)")
    parser.add_argument("--ui", action="store_true",
                        help="Force open the graphical interface")
    parser.add_argument("--format", "-f",
                        choices=list(FORMAT_CODEC_MAP.keys()),
                        default=os.getenv("FORMAT", "best"))
    parser.add_argument("--quality", "-q", default="0")
    parser.add_argument("--output", "-o",
                        default=os.getenv("OUTPUT_FOLDER", "./downloads"))
    parser.add_argument("--no-playlist", action="store_true", default=True)
    args = parser.parse_args()

    if args.ui or args.url is None:
        run_gui()
    else:
        run_headless(
            url=args.url,
            output_dir=args.output,
            fmt=args.format,
            quality=args.quality,
            no_playlist=args.no_playlist,
        )


if __name__ == "__main__":
    main()