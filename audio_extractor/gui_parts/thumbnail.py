import io
import requests
import threading
import urllib.request
from PIL import Image,ImageTk

def draw_thumb_placeholder(canvas, w, h, fg, bg):
    """Draw a placeholder when no thumbnail is available."""
    canvas.delete("all")
    canvas.create_rectangle(0, 0, w, h, fill=bg, outline="")
    cx, cy = w // 2, h // 2
    canvas.create_oval(cx-14, cy+6,  cx-2,  cy+18, fill=fg, outline="")
    canvas.create_oval(cx+4,  cy-4,  cx+16, cy+8,  fill=fg, outline="")
    canvas.create_line(cx-2,  cy+12, cx-2,  cy-16, fill=fg, width=2)
    canvas.create_line(cx+16, cy+2,  cx+16, cy-22, fill=fg, width=2)
    canvas.create_line(cx-2,  cy-16, cx+16, cy-22, fill=fg, width=2)

def _load_thumbnail(urls, thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2, root):
    if isinstance(urls, str):
        urls = [urls]
    img = None
    for url_or_path in urls:
        try:
            if url_or_path.startswith("http"):
                try:
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
        root.after(0, lambda: draw_thumb_placeholder(
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
                thumb_canvas.delete("all")
                thumb_canvas.create_image(0, 0, anchor="nw", image=photo)
                thumb_canvas._thumb_ref = photo  # <-- keep reference alive on the widget
                thumb_canvas.update_idletasks()
            except Exception as e:
                print(f"[thumb _paint error] {e}")

        root.after(0, _paint)
    except Exception as e:
        print(f"[thumb process error] {e}")
        root.after(0, lambda: draw_thumb_placeholder(
            thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2))

def set_thumbnail(urls, thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2, root):
    """Start thumbnail loading in background thread."""
    if isinstance(urls, str):
        urls = [urls]
    threading.Thread(
        target=_load_thumbnail,
        args=(urls, thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2, root),
        daemon=True
    ).start()

def clear_thumbnail(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2, _thumb_ref):
    thumb_canvas.delete("all")
    thumb_canvas._thumb_ref = None
    draw_thumb_placeholder(thumb_canvas, THUMB_W, THUMB_H, FG_DIM, SURFACE2)
    _thumb_ref[0] = None
