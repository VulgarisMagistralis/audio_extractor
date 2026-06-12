"""Graphical user interface for Audio Extractor (Tkinter)."""

import os
import sys
import colorsys
import threading
import subprocess
import tkinter as tk
import tkinter
import tkinter.font as tkFont
from PIL import Image, ImageTk
from tkinter import ttk, filedialog, messagebox
from audio_extractor.title_bar import TitleBar
from .service.download_2 import DownloadManager
from .gui_parts.thumbnail import *
from .button_state import ButtonState
from .utils import check_dependencies
from .metadata import FORMAT_CODEC_MAP, safe_stem
from .config import load_config, save_config, _CONFIG_PATH
from .downloader import build_ydl_opts, fetch_info

def run_gui():
    """Launch the graphical user interface."""
    _cfg = load_config()
    BG = _cfg["bg"]
    ACCENT = _cfg["accent"]
    FG = _cfg["fg"]
    FG_DIM = _cfg["fg_dim"]
    root = tk.Tk()
    root.title("Audio Extractor")
    root.configure(bg=BG)
    root.minsize(860, 600)
    if sys.platform.startswith("linux"):
        try:
            root.wm_attributes("-type", "splash")
        except Exception:
            root.overrideredirect(True)
    else:
        root.overrideredirect(True)

    titlebar = TitleBar(root, bg_color=BG)
    titlebar.pack(side="top", fill="x")
    _rsz = {"x": 0, "y": 0, "w": 0, "h": 0, "wx": 0, "wy": 0, "edge": ""}
    EDGE = 6

    def _edge_cursor(ex, ey, w, h):
        l = ex < EDGE; r = ex > w - EDGE
        t = ey < EDGE; b = ey > h - EDGE
        if t and l: return "top_left_corner", "nw"
        if t and r: return "top_right_corner", "ne"
        if b and l: return "bottom_left_corner", "sw"
        if b and r: return "bottom_right_corner", "se"
        if t: return "top_side", "n"
        if b: return "bottom_side", "s"
        if l: return "left_side", "w"
        if r: return "right_side", "e"
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
        _rsz["x"] = e.x_root; _rsz["y"] = e.y_root
        _rsz["w"] = root.winfo_width()
        _rsz["h"] = root.winfo_height()
        _rsz["wx"] = root.winfo_x()
        _rsz["wy"] = root.winfo_y()

    def _win_resize(e):
        if not _rsz["edge"]:
            return
        dx = e.x_root - _rsz["x"]
        dy = e.y_root - _rsz["y"]
        x, y = _rsz["wx"], _rsz["wy"]
        w, h = _rsz["w"], _rsz["h"]
        edge = _rsz["edge"]
        if "e" in edge: w = max(660, w + dx)
        if "w" in edge: nw = max(660, w - dx); x += w - nw; w = nw
        if "s" in edge: h = max(400, h + dy)
        if "n" in edge: nh = max(400, h - dy); y += h - nh; h = nh
        root.geometry(f"{w}x{h}+{x}+{y}")

    root.bind("<Motion>", _win_motion)
    root.bind("<ButtonPress-1>", _win_press)
    root.bind("<B1-Motion>", _win_resize)
    root.config(highlightthickness=1, highlightbackground=BG)

    _face = "SF Pro Display" if sys.platform == "darwin" else "Segoe UI"
    _face_mono = "SF Mono" if sys.platform == "darwin" else "Consolas"
    _base = _cfg.get("font_size", 13 if sys.platform == "darwin" else 11)

    FONT_UI = tkFont.Font(family=_face, size=_base)
    FONT_SM = tkFont.Font(family=_face, size=_base - 2)
    FONT_MONO = tkFont.Font(family=_face_mono, size=_base - 2)
    FONT_BIG = tkFont.Font(family=_face, size=_base + 9, weight="bold")
    _colors = {"bg": [BG], "accent": [ACCENT], "fg": [FG], "fg_dim": [FG_DIM]}
    _COLOUR_DEFS = [
            ("accent", "Accent", _colors["accent"]),
            ("bg", "Background", _colors["bg"]),
            ("fg", "Text", _colors["fg"]),
            ("fg_dim", "Subtitle Text", _colors["fg_dim"]),
        ]
    THUMB_W, THUMB_H = 120, 120

    url_var = tk.StringVar()
    fmt_var = tk.StringVar(value=os.getenv("FORMAT", _cfg.get("fmt", "best")))
    quality_var = tk.StringVar(value="0")
    output_var = tk.StringVar(value=os.path.expanduser(
        os.getenv("OUTPUT_FOLDER", _cfg.get("output_dir", "~/Downloads/audio"))))
    no_playlist = tk.BooleanVar(value=True)
    filename_var = tk.StringVar()
    filename_edited = [False]
    status_var = tk.StringVar(value="Ready")
    speed_var = tk.StringVar(value="")
    eta_var = tk.StringVar(value="")
    meta_title_var = tk.StringVar(value="")
    meta_artist_var = tk.StringVar(value="")
    meta_dur_var = tk.StringVar(value="")
    meta_src_var = tk.StringVar(value="")
    _thumb_ref = [None]
    _info_visible = [False]
    my_vars = {                                                                                                                                                   
        'url': url_var,
        'filename': filename_var,
        'status': status_var,
        'speed': speed_var,
        'eta': eta_var,
        'output': output_var,
        'fmt': fmt_var,
        'no_playlist': no_playlist,
        'quality': quality_var,
        'colors':_colors
    }
    my_states = {
        'filename_edited': filename_edited,
        'fn_trace_paused': [False]
    }

    def frame(parent, **kw):
        return tk.Frame(parent, bg=kw.pop("bg", BG), **kw)

    def label(parent, text="", fg=FG, font=FONT_UI, fg_cat="fg", **kw):
        lbl = tk.Label(parent, text=text, fg=fg, bg=kw.pop("bg", BG), font=font, **kw)
        lbl._fg_cat = fg_cat
        return lbl

    def entry(parent, textvariable=None, width=40, **kw):
        e = tk.Entry(parent, textvariable=textvariable, width=width,
                     bg=BG, fg=FG, insertbackground=ACCENT,
                     relief="flat", font=FONT_MONO,
                     highlightthickness=1, highlightbackground=BG,
                     highlightcolor=ACCENT, **kw)
        e.bind("<Control-a>", lambda e: (e.widget.select_range(0, "end"),
                                         e.widget.icursor("end"), "break"))
        return e

    def accent_btn(parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=ACCENT, fg="#0d0d0f",
                         font=tkFont.Font(family=_face, size=_base, weight="bold"),
                         relief="flat", cursor="hand2",
                         activebackground=BG, activeforeground="#0d0d0f",
                         padx=18, pady=8, **kw)

    def ghost_btn(parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=BG, fg=FG_DIM, font=FONT_SM,
                         relief="flat", cursor="hand2",
                         activebackground=BG, activeforeground=FG,
                         padx=10, pady=5,
                         highlightthickness=1, highlightbackground=BG, **kw)

    def seg_btn(parent, text, command):
        return tk.Button(parent, text=text, command=command,
                         bg=BG, fg=FG_DIM, font=FONT_SM,
                         relief="flat", cursor="hand2",
                         padx=10, pady=4,
                         highlightthickness=1, highlightbackground=BG)

    def divider(parent):
        return tk.Frame(parent, bg=BG, height=1)

    style = ttk.Style()
    style.theme_use("default")
    style.configure("App.TNotebook", background=BG, borderwidth=0, tabmargins=0)
    style.configure("App.TNotebook.Tab", background=BG, foreground=FG_DIM,
                    font=(_face, _base - 1), padding=(16, 6), borderwidth=0)
    style.map("App.TNotebook.Tab", background=[("selected", BG)],
              foreground=[("selected", ACCENT)])
    nb = ttk.Notebook(root, style="App.TNotebook")
    nb.pack(fill="both", expand=True)

    tab_dl = frame(nb, bg=BG)
    tab_cfg = frame(nb, bg=BG)
    nb.add(tab_dl, text="  Download  ")
    nb.add(tab_cfg, text="  Settings  ")

    # Download tab header
    hdr = frame(tab_dl)
    hdr.pack(fill="x", padx=24, pady=(20, 4))
    label(hdr, "Audio Extractor", font=FONT_BIG, fg=ACCENT).pack(side="left")
    label(hdr, "yt-dlp powered", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left", padx=(8, 0), pady=(8, 0))
    divider(tab_dl).pack(fill="x", padx=24, pady=8)

    # URL row
    url_row = frame(tab_dl)
    url_row.pack(fill="x", padx=24, pady=(4, 2))
    label(url_row, "URL", fg=FG_DIM, font=FONT_SM, width=9, anchor="w", fg_cat="fg_dim").pack(side="left", padx=(0, 8))
    entry(url_row, textvariable=url_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    ghost_btn(url_row, "✕", lambda: url_var.set("")).pack(side="left", padx=(0, 8))

    def _on_url_changed(*_):
        filename_edited[0] = False
        fn_trace_paused[0] = True
        filename_var.set("")
        fn_trace_paused[0] = False
        set_button_idle()
    
    url_var.trace_add("write", _on_url_changed)

    # Output dir row
    out_row = frame(tab_dl)
    out_row.pack(fill="x", padx=24, pady=2)
    label(out_row, "Output dir", fg=FG_DIM, font=FONT_SM, width=9, anchor="w", fg_cat="fg_dim").pack(side="left", padx=(0, 8))
    entry(out_row, textvariable=output_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    def browse_dir():
        d = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if d:
            output_var.set(d)
    ghost_btn(out_row, "Browse...", browse_dir).pack(side="left")

    # Filename row
    fn_row = frame(tab_dl)
    fn_row.pack(fill="x", padx=24, pady=2)
    label(fn_row, "Filename", fg=FG_DIM, font=FONT_SM, width=9, anchor="w", fg_cat="fg_dim").pack(side="left", padx=(0, 8))
    fn_entry = entry(fn_row, textvariable=filename_var)
    fn_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    
    def _clear_filename():
        filename_edited[0] = False
        fn_trace_paused[0] = True
        filename_var.set("")
        fn_trace_paused[0] = False
    ghost_btn(fn_row, "✕", _clear_filename).pack(side="left", padx=(0, 8))
    label(fn_row, "(auto-filled after fetch; edit to override)", fg=FG_DIM, font=FONT_SM).pack(side="left")
    
    def _on_filename_changed(*_):
        if not fn_trace_paused[0]:
            filename_edited[0] = True
    fn_trace_paused = [False]
    filename_var.trace_add("write", _on_filename_changed)

    # Format segmented control
    fmt_row = frame(tab_dl)
    fmt_row.pack(fill="x", padx=24, pady=(6, 2))
    label(fmt_row, "Format", fg=FG_DIM, font=FONT_SM, width=9, anchor="w", fg_cat="fg_dim").pack(side="left", padx=(0, 8))
    fmt_seg = frame(fmt_row)
    fmt_seg.pack(side="left")
    _fmt_btns = {}

    def _select_fmt(f):
        fmt_var.set(f)
        for name, btn in _fmt_btns.items():
            if name == f:
                btn.config(bg=ACCENT, fg="#0d0d0f", highlightbackground=ACCENT)
            else:
                btn.config(bg=BG, fg=FG_DIM, highlightbackground=BG)

    for i, fmt_name in enumerate(FORMAT_CODEC_MAP):
        b = seg_btn(fmt_seg, fmt_name.upper(), lambda f=fmt_name: _select_fmt(f))
        b.grid(row=0, column=i, padx=(0, 2))
        _fmt_btns[fmt_name] = b
    _select_fmt(fmt_var.get())

    label(fmt_row, "  Q", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left", padx=(12, 4))
    entry(fmt_row, textvariable=quality_var, width=5).pack(side="left")
    label(fmt_row, "(mp3: 0=best...9  |  aac/opus: kbps)", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left", padx=8)

    pl_row = frame(tab_dl)
    pl_row.pack(fill="x", padx=24, pady=(6, 4))
    label(pl_row, "", width=9).pack(side="left")
    label(pl_row, "Single track only (skip playlist)", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left")

    divider(tab_dl).pack(fill="x", padx=24, pady=(8, 0))

    # Info card
    info_card = frame(tab_dl, bg=BG)
    info_outer = frame(info_card, bg=BG)
    info_outer.pack(fill="x", padx=12, pady=10)

    thumb_canvas = tk.Canvas(info_outer, width=THUMB_W, height=THUMB_H,
                             bg=BG, highlightthickness=1,
                             highlightbackground=BG)
    thumb_canvas.pack(side="left", padx=(4, 16))
    draw_thumb_placeholder(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, BG)

    meta_inner = frame(info_outer, bg=BG)
    meta_inner.pack(side="left", fill="both", expand=True)

    def _meta_row(parent, key, var, fg_val=FG):
        r = frame(parent, bg=BG)
        r.pack(fill="x", pady=2)
        label(r, key, fg=FG_DIM, font=FONT_SM, width=8, anchor="w", bg=BG, fg_cat="fg_dim").pack(side="left")
        label(r, textvariable=var, fg=fg_val, font=FONT_SM, anchor="w", bg=BG).pack(side="left")

    _meta_row(meta_inner, "Title", meta_title_var)
    _meta_row(meta_inner, "Artist", meta_artist_var)
    dur_src = frame(meta_inner, bg=BG)
    dur_src.pack(fill="x", pady=2)
    label(dur_src, "Length", fg=FG_DIM, font=FONT_SM, width=8, anchor="w", bg=BG, fg_cat="fg_dim").pack(side="left")
    label(dur_src, textvariable=meta_dur_var, fg=FG, font=FONT_SM, bg=BG).pack(side="left")
    label(dur_src, "  Source", fg=FG_DIM, font=FONT_SM, bg=BG, fg_cat="fg_dim").pack(side="left", padx=(16, 4))
    label(dur_src, textvariable=meta_src_var, fg=BG, font=FONT_SM, bg=BG).pack(side="left")

    pb_frame = frame(tab_dl)

    def _show_info_card():
        if not _info_visible[0]:
            info_card.pack(fill="x", padx=24, pady=(4, 4), before=pb_frame)
            _info_visible[0] = True

    pb_frame = frame(tab_dl)
    pb_frame.pack(fill="x", padx=24, pady=(8, 2))
    pb_canvas = tk.Canvas(pb_frame, bg=BG, height=6,
                          highlightthickness=0, relief="flat")
    pb_canvas.pack(fill="x")
    pb_canvas.bind("<Configure>", lambda e: download_manager.redraw_bar())

    st_row = frame(tab_dl)
    st_row.pack(fill="x", padx=24, pady=(2, 0))
    label(st_row, textvariable=status_var, fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left")
    label(st_row, textvariable=speed_var, fg=ACCENT, font=FONT_SM).pack(side="left", padx=12)
    label(st_row, textvariable=eta_var, fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(side="left")

    btn_row = frame(tab_dl)
    btn_row.pack(fill="x", padx=24, pady=(14, 20))
    download_button = accent_btn(btn_row, "Fetch Info", lambda: None)
    download_button.pack(side="left")
    _download_button_state = ButtonState.IDLE
      
    def set_button_idle():
        global _download_button_state
        _download_button_state = ButtonState.IDLE
        download_button.config(text="Fetch Info", state="normal", command=do_fetch_info)

    def set_button_fetched():
        global _download_button_state
        _download_button_state = ButtonState.FETCHED
        download_button.config(text="Download", state="normal", command=download_manager.do_download)

    download_manager = DownloadManager(                                                                                                                           
            root = root,
            vars_dict = my_vars,
            pb_canvas = pb_canvas,
            state_vars = my_states,
            download_button = download_button,
            set_button_interface = set_button_idle,
            download_state_ref = _download_button_state
        )
    def do_fetch_info():
        if _download_button_state == ButtonState.DOWNLOADING:
            return
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a URL first.")
            return
        status_var.set("Fetching info...")
        meta_title_var.set("...")
        meta_artist_var.set("")
        meta_dur_var.set("")
        meta_src_var.set("")
        root.after(0, lambda: clear_thumbnail(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, BG, _thumb_ref))
        root.after(0, _show_info_card)

        def worker():
            try:
                check_dependencies(raise_on_missing=True)
                opts = build_ydl_opts(
                    output_var.get() or "~/Downloads/audio",
                    fmt_var.get(), quality_var.get(),
                    no_playlist.get(),
                )
                info = fetch_info(url, opts)
                title = info.get("title", "Unknown")
                artist = (info.get("artist") or info.get("uploader")
                            or info.get("channel") or "Unknown")
                duration = info.get("duration")
                dur_s = (f"{int(duration)//60}:{int(duration)%60:02d}"
                            if duration else "?")
                acodec = info.get("acodec", "?")
                abr = info.get("abr", "?")

                thumbnails = info.get("thumbnails") or []
                def _pick_thumbnail(thumbnails: list[dict], fallback: str | None = None) -> str | None:
                    # Only consider entries with known dimensions
                    sized = [t for t in thumbnails if t.get("width") and t.get("height") and t.get("url")]
                    
                    if not sized:
                        # Fall back to any .jpg, then any URL, then yt-dlp's own pick
                        jpg = next((t["url"] for t in thumbnails if t.get("url", "").endswith(".jpg")), None)
                        return jpg or next((t["url"] for t in thumbnails if t.get("url")), fallback)
                    
                    def _score(t):
                        area = t["width"] * t["height"]
                        fmt_bonus = 1 if t["url"].endswith(".jpg") else 0
                        return (area, fmt_bonus)
                    
                    return max(sized, key=_score)["url"]
    
                thumb_urls = _pick_thumbnail(thumbnails)
                root.after(0, meta_title_var.set, title)
                root.after(0, meta_artist_var.set, artist)
                root.after(0, meta_dur_var.set, dur_s)
                root.after(0, meta_src_var.set, f"{acodec} @ {abr} kbps")
                root.after(0, status_var.set, "Ready to download")
                root.after(0, set_button_fetched)
# todo modify metadata to remove 'offical..'
                def _set_filename(a=artist, t=title):
                    fn_trace_paused[0] = True
                    filename_var.set(safe_stem(f"{t}"))
                    fn_trace_paused[0] = False
                if not filename_edited[0]:
                    root.after(0, _set_filename)
                if thumb_urls:
                    threading.Thread(target=set_thumbnail, args=(
                        thumb_urls, thumb_canvas, THUMB_W, THUMB_H, FG_DIM, BG, root
                    ), daemon=True).start()
            except Exception as e:
                root.after(0, status_var.set, f"Error: {e}")
                root.after(0, meta_title_var.set, "-")
                root.after(0, set_button_idle)

        threading.Thread(target=worker, daemon=True).start()

    set_button_idle()

    # Font size slider
    font_row = frame(tab_dl)
    font_row.pack(fill="x", padx=24, pady=(0, 16))

    font_size_var = tk.IntVar(value=_base)

    def _update_fonts(val):
        sz = int(val)
        FONT_UI.configure(size=sz)
        FONT_SM.configure(size=max(sz - 2, 7))
        FONT_MONO.configure(size=max(sz - 2, 7))
        FONT_BIG.configure(size=sz + 9)
        for btn in [download_button]:
            try:
                btn.configure(font=tkFont.Font(family=_face, size=sz, weight="bold"))
            except Exception:
                pass

    # Settings tab
    cfg_hdr = frame(tab_cfg)
    cfg_hdr.pack(fill="x", padx=24, pady=(20, 4))
    label(cfg_hdr, "Settings", font=FONT_BIG, fg=ACCENT).pack(side="left")
    divider(tab_cfg).pack(fill="x", padx=24, pady=8)

    _accent = [ACCENT]
    _bg = [BG]
    _fg = [FG]
    _fg_dim = [FG_DIM]

    def _recolor_all():
        new_bg = _bg[0]
        new_fg = _fg[0]
        new_fg_dim = _fg_dim[0]
        def _walk(w):
            cls = w.winfo_class()
            try:
                if cls in ("Frame", "Label", "Checkbutton"):
                    if w.cget("bg") not in (_accent[0]):
                        w.config(bg=new_bg)
                    if cls == "Label":
                        try:
                            cat = w._fg_cat if hasattr(w, "_fg_cat") else "fg"
                            if cat == "fg_dim":
                                w.config(fg=new_fg_dim)
                            else:
                                w.config(fg=new_fg)
                        except Exception:
                            pass
                elif cls == "Button":
                    if w.cget("bg") not in (_accent[0], _bg[0]):
                        w.config(bg=new_bg, activebackground=new_bg)
            except Exception:
                pass
            for child in w.winfo_children():
                _walk(child)
        _walk(root)
        for widget in root.window.winfo_children():
          try:
              widget.configure(bg=new_bg)
          except (AttributeError,tkinter.TclError):
              pass

        root.config(bg=new_bg)
        if titlebar:
            titlebar.config(bg=new_bg)

    label(tab_cfg, "Colours", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(anchor="w", padx=24, pady=(4, 0))

    _swatches = {}
    def _make_swatch(parent, current_hex):
        sw = tk.Frame(parent, bg=current_hex, width=32, height=32,
                      cursor="hand2")
        sw.pack(side="left", padx=(0, 8))
        sw.pack_propagate(False)
        return sw

    def _open_colour_picker(initial_hex, title, on_select):
        popup = tk.Toplevel(root)
        popup.title(title)
        popup.configure(bg=BG)
        popup.resizable(False, False)
        popup.transient(root)
        popup.wm_attributes("-topmost", True)
        popup.after(50, popup.grab_set)
        popup.after(50, popup.lift)

        PAD = 16
        SW = 260
        HH = 18

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

        hue_canvas = tk.Canvas(popup, width=SW, height=HH, highlightthickness=0, bd=0)
        hue_canvas.pack(padx=PAD, pady=(PAD, 4))

        def _draw_hue():
            hue_canvas.delete("all")
            for x in range(SW):
                h = x / SW
                r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                col = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
                hue_canvas.create_line(x, 0, x, HH, fill=col)
            cx = int(state["h"] * SW)
            hue_canvas.create_rectangle(cx-2, 0, cx+2, HH, outline="white", fill="", width=2)

        def _hue_click(e):
            state["h"] = max(0.0, min(1.0, e.x / SW))
            _draw_hue()
            _draw_sv()
            _sync_hex()
        hue_canvas.bind("<Button-1>", _hue_click)
        hue_canvas.bind("<B1-Motion>", _hue_click)

        sv_canvas = tk.Canvas(popup, width=SW, height=SW, highlightthickness=0, bd=0)
        sv_canvas.pack(padx=PAD, pady=4)
        _sv_img = [None]

        def _draw_sv():
            try:
                img = Image.new("RGB", (SW, SW))
                px = img.load()
                h = state["h"]
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
                sv_canvas.delete("all")
                h = state["h"]
                for x in range(0, SW, 2):
                    s = x / SW
                    for y in range(0, SW, 2):
                        v = 1.0 - y / SW
                        r, g, b = colorsys.hsv_to_rgb(h, s, v)
                        col = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
                        sv_canvas.create_rectangle(x, y, x+2, y+2, fill=col, outline="")
            cx = int(state["s"] * SW)
            cy = int((1.0 - state["v"]) * SW)
            sv_canvas.create_oval(cx-7, cy-7, cx+7, cy+7, outline="white", width=2)
            sv_canvas.create_oval(cx-5, cy-5, cx+5, cy+5, outline="black", width=1)

        def _sv_click(e):
            state["s"] = max(0.0, min(1.0, e.x / SW))
            state["v"] = max(0.0, min(1.0, 1.0 - e.y / SW))
            _draw_sv()
            _sync_hex()

        sv_canvas.bind("<Button-1>", _sv_click)
        sv_canvas.bind("<B1-Motion>", _sv_click)
        bottom = frame(popup, bg=BG)
        bottom.pack(fill="x", padx=PAD, pady=(8, PAD))

        preview = tk.Frame(bottom, width=40, height=32, bg=initial_hex,
                           highlightthickness=1, highlightbackground=BG)
        preview.pack(side="left", padx=(0, 10))
        preview.pack_propagate(False)

        hex_var = tk.StringVar(value=initial_hex)
        hex_entry = tk.Entry(bottom, textvariable=hex_var, width=10,
                             bg=BG, fg=FG, insertbackground=ACCENT,
                             relief="flat", font=FONT_MONO,
                             highlightthickness=1, highlightbackground=BG)
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

        popup.after(50, _draw_hue)
        popup.after(50, _draw_sv)
        _sync_hex()

    pal_frame = frame(tab_cfg)
    pal_frame.pack(fill="x", padx=24, pady=6)
    def create_apply_fn(ref_list, key_str):                                                                                                               
            def apply(new_color):                                                                                                                             
                ref_list[0] = new_color                                                                                                                       
                _colors[key_str][0] = new_color                                                                                                               
                _recolor_all()                                                                                                                                
                if key_str in _swatches:                                                                                                                      
                    _swatches[key_str].config(bg=new_color)                                                                                                   
            return apply               

    for i, (key, lbl, ref) in enumerate(_COLOUR_DEFS):
      cell = frame(pal_frame)
      cell.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 40), pady=5)
      sw = _make_swatch(cell, ref[0]) 
      _swatches[key] = sw
      apply_fn = create_apply_fn(ref, key)
      sw.bind("<Button-1>", lambda e, a=apply_fn: _open_colour_picker(                                                                                      
              ref[0],                                                                                                                                           
              "Pick colour",                                                                                                                                    
              lambda c: a(c)                                                                                                                                    
          ))
      label(cell, lbl, fg=FG, font=FONT_SM, fg_cat="fg_dim").pack(side="left", padx=(8, 0))

    divider(tab_cfg).pack(fill="x", padx=24, pady=(12, 4))

    label(tab_cfg, "Font size", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(anchor="w", padx=24, pady=(4, 0))
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

    label(tab_cfg, "Default output dir", fg=FG_DIM, font=FONT_SM, fg_cat="fg_dim").pack(anchor="w", padx=24, pady=(4, 0))
    outdir_row = frame(tab_cfg)
    outdir_row.pack(fill="x", padx=24, pady=6)
    entry(outdir_row, textvariable=output_var, width=36).pack(side="left", padx=(0, 8))
    
    def _br2():
        d = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if d: output_var.set(d)
    
    ghost_btn(outdir_row, "Browse...", _br2).pack(side="left")
    divider(tab_cfg).pack(fill="x", padx=24, pady=(16, 8))
    save_row = frame(tab_cfg)
    save_row.pack(fill="x", padx=24, pady=(0, 20))
    _save_lbl = tk.StringVar(value="Save settings")
    
    def _current_cfg():
        return {k: _colors[k][0] for k in _colors} | {
        "font_size": font_size_var.get(),
        "output_dir": output_var.get(),
        "fmt": fmt_var.get(),
    }

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

    def _open_config_dir():
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        folder = str(_CONFIG_PATH.parent)
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", folder])
        else:
            subprocess.Popen(["explorer", folder])

    cfg_path_row = frame(tab_cfg)
    cfg_path_row.pack(fill="x", padx=24, pady=(4, 0))
    label(cfg_path_row, "Config", fg=FG_DIM, font=FONT_SM, width=9, anchor="w", fg_cat="fg_dim").pack(side="left", padx=(0, 8))
    path_lbl = tk.Label(cfg_path_row, text=str(_CONFIG_PATH),
                        fg=FG_DIM, bg=BG, font=FONT_SM,
                        cursor="hand2", anchor="w")
    path_lbl._fg_cat = "fg_dim"
    path_lbl.pack(side="left")
    path_lbl.bind("<Enter>", lambda e: path_lbl.config(fg=ACCENT))
    path_lbl.bind("<Leave>", lambda e: path_lbl.config(fg=_fg_dim[0]))
    path_lbl.bind("<Button-1>", lambda e: _open_config_dir())

    root.mainloop()
