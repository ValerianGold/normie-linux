#!/usr/bin/env python3
"""Regenerate the artwork the Normie packages ship, from branding/normie-logo.svg.

Needs Pillow and rsvg-convert. You never have to run this to build an ISO: the generated files are
committed. Run it only after changing the logo:

    python3 packaging/make-assets.py

Everything written here is derived from branding/normie-logo.svg; nothing is taken from Fedora's artwork.
"""
import os
import random
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SVG = os.path.join(ROOT, "branding", "normie-logo.svg")
LOGOS = os.path.join(ROOT, "packaging", "normie-logos", "files")
BACKGROUNDS = os.path.join(ROOT, "packaging", "normie-backgrounds-kde", "files")
LNF = os.path.join(ROOT, "packaging", "normie-lookandfeel", "files")

ICON_SIZES = (16, 22, 24, 32, 36, 48, 64, 96, 128, 256)
NAVY_TOP, NAVY_BOTTOM = (28, 34, 54), (11, 14, 24)         # dark navy used behind the logo in the generated images
EMBER = [(255, 232, 92), (255, 201, 51), (255, 163, 38), (247, 122, 29), (220, 76, 23), (169, 42, 20)]


def logo(size):
    """The logo at a given size, always rendered large first so small sizes are smooth."""
    big = subprocess.run(["rsvg-convert", "-w", "1024", "-h", "1024", SVG], check=True, capture_output=True).stdout
    import io
    im = Image.open(io.BytesIO(big)).convert("RGBA")
    return im.resize((size, size), Image.LANCZOS)


def save(im, *parts, **kw):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True, **kw)
    return path


def gradient(w, h, top=NAVY_TOP, bottom=NAVY_BOTTOM):
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
    return col.resize((w, h))


def panel(w, h, logo_size, logo_at="center"):
    """A navy panel with the logo on it, for the installer and boot images."""
    im = gradient(w, h).convert("RGBA")
    mark = logo(logo_size)
    x = (w - logo_size) // 2 if logo_at == "center" else 12
    y = (h - logo_size) // 2
    im.alpha_composite(mark, (x, y))
    return im


def wallpaper(w, h, seed=45):
    """Dark navy, a warm glow rising from the bottom, and pixel embers drifting up (the logo's fire)."""
    rnd = random.Random(seed)
    im = gradient(w, h, (26, 32, 52), (9, 11, 20)).convert("RGBA")
    # warm glow along the bottom edge
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-w * 0.15, h * 0.82, w * 1.15, h * 1.55), fill=(196, 62, 22, 135))
    gd.ellipse((w * 0.20, h * 0.93, w * 0.80, h * 1.45), fill=(247, 122, 29, 105))
    glow = glow.filter(ImageFilter.GaussianBlur(h * 0.085))
    im.alpha_composite(glow)
    # embers: crisp squares, bigger and brighter near the bottom, fading as they rise
    unit = max(2, h // 270)                     # one "pixel" of the fire, scales with the picture
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(int(w * h / (unit * unit) / 520)):
        x = rnd.randrange(0, w // unit) * unit
        rise = rnd.random() ** 1.8                # 0 = at the bottom, 1 = top; most embers stay low
        y = int((h - unit) * (1 - rise))
        heat = min(len(EMBER) - 1, int(rise * len(EMBER) * 1.5 + rnd.random()))
        alpha = int(235 * (1 - rise) ** 0.9) + 20
        s = unit * (2 if rnd.random() < 0.18 and rise < 0.5 else 1)
        ld.rectangle((x, y, x + s - 1, y + s - 1), fill=EMBER[heat] + (alpha,))
    im.alpha_composite(layer)
    # no logo on the wallpaper: the Start button and the login screen already carry it
    return im.convert("RGB")


def main():
    if not os.path.exists(SVG):
        sys.exit(f"cannot find {SVG}")
    # ---- normie-logos
    os.makedirs(LOGOS, exist_ok=True)
    shutil.copyfile(SVG, os.path.join(LOGOS, "normie-logo-icon.svg"))
    for s in ICON_SIZES:
        save(logo(s), LOGOS, "icons", f"{s}.png")
    save(logo(256), LOGOS, "pixmaps", "normie-logo.png")
    save(logo(128), LOGOS, "pixmaps", "normie-logo-small.png")
    white = logo(240)                                       # a flat white-on-transparent mark for dark panels
    save(white, LOGOS, "pixmaps", "system-logo-white.png")
    save(logo(128), LOGOS, "pixmaps", "bootloader", "bootlogo_128.png")
    save(logo(256), LOGOS, "pixmaps", "bootloader", "bootlogo_256.png")
    save(logo(128), LOGOS, "plymouth", "watermark.png")
    # installer (sizes are the ones the installer expects)
    save(panel(800, 88, 72, "left"), LOGOS, "anaconda", "anaconda_header.png")
    save(panel(1040, 132, 100, "left"), LOGOS, "anaconda", "topbar-bg.png")
    save(gradient(406, 767).convert("RGBA"), LOGOS, "anaconda", "sidebar-bg.png")
    save(logo(128), LOGOS, "anaconda", "sidebar-logo.png")
    save(panel(416, 265, 160), LOGOS, "anaconda", "splash.png")
    save(panel(416, 265, 160), LOGOS, "anaconda", "progress_first.png")
    save(panel(640, 300, 200).convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=64),
         LOGOS, "anaconda", "syslinux-splash.png")
    save(panel(640, 480, 240), LOGOS, "anaconda", "syslinux-vesa-splash.png")
    # ---- normie-backgrounds-kde
    for w, h in ((1920, 1080), (3840, 2160)):
        save(wallpaper(w, h), BACKGROUNDS, "images", f"{w}x{h}.jpg", quality=88, progressive=True)
    save(wallpaper(600, 338), BACKGROUNDS, "screenshot.jpg", quality=85)
    # ---- normie-lookandfeel
    save(wallpaper(1280, 720).convert("RGB"), LNF, "previews", "preview.png")
    save(wallpaper(1920, 1080), LNF, "previews", "fullscreenpreview.jpg", quality=85)
    print("Wrote the artwork under packaging/*/files/")


if __name__ == "__main__":
    main()
