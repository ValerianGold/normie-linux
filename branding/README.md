# Branding

`normie-logo.svg` is the **draft v0** logo: a white letter N with a flame on its right stem, on a dark
rounded badge. The badge keeps the white N visible on light and dark backgrounds. It was drawn for this
project as an original work and is plain SVG shapes: no fonts, no embedded images, no scripts.

| Part | Value |
|---|---|
| Canvas | 512 x 512, square |
| Badge | rounded square, corner radius 112, gradient `#1c2236` to `#0b0e18` |
| N | white `#ffffff`, three shapes (two stems and a diagonal) |
| Flame | gradient `#ff4d12` to `#ffb52e`, middle layer `#ffd23f`, core `#fff1b8` |

It stays recognizable down to about 24 pixels; below that the flame becomes a dot, which is fine.

## Before it is final

- Search trademark databases for lookalike marks. Flame-and-letter logos are common.
- Decide the license for the artwork (it is currently covered by the repository's GPL-3.0-or-later).
- Make a one-color version (N and flame in a single color, no badge) for panel and tray icons, which
  Plasma recolors to match the theme.

## Where a logo is used (all generated from this one file by the future `normie-logos` package)

Start menu button, login screen, boot splash, installer sidebar and header, GRUB and ISO boot menu,
wallpapers, the `LOGO=` entry in `/etc/os-release`, the About page. Sizes come from the SVG, for
example on Fedora with librsvg:

```
rsvg-convert -w 256 -h 256 branding/normie-logo.svg -o normie-logo-256.png
```
