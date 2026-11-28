# Normie Linux logo

`normie-logo.svg` is the logo. The system uses it through the `normie-logos` package for the Start button, the boot and
installer screens, `/etc/os-release` (`LOGO=`), the About page and the GitHub page. It contains no Fedora artwork.

Source and licence: see `NOTICE.md`.

## Rules for the file

`tests/test_branding.py` checks these, whatever the design looks like:

- **Square.** The `viewBox` must be square (for a tall or wide drawing, add empty margin on the short sides). The icons
  are rendered 1024 by 1024 and a non-square file would come out stretched.
- **Plain shapes only**: paths, rectangles, circles, polygons, gradients and a `<style>` block. No text or fonts (they
  render differently on every computer), scripts, images, links or outside references. That keeps it safe to ship.
- Under 200 KB.

A transparent background is fine. Check the result at 22, 48 and 256 px on both a light and a dark background before
committing.

## Changing it

1. Replace `branding/normie-logo.svg`.
2. `python3 packaging/make-assets.py` regenerates the icons, installer images and boot artwork (needs Pillow and
   `rsvg-convert`; a test fails until you do).
3. `python3 -m unittest discover -s tests`.
4. To reach systems that are already installed, raise the packages' versions with `tools/bump-package.sh` and run
   `tools/publish-packages.sh` (`docs/PACKAGE-REPOSITORY.md`, "Changing something later").

Sizes can also be made by hand, for example on Fedora with librsvg:

```
rsvg-convert -w 256 -h 256 branding/normie-logo.svg -o normie-logo-256.png
```
