# Normie Linux logo

`normie-logo.svg` is the logo: a white letter **N** on a dark rounded badge, wrapped in shaded pixel-art flames
(16/32-bit style, with six heat shades from yellow to dark red). The letter itself is the heat source: the fire is hottest
right against every outer edge and cools outwards, so the sides and the top burn as one continuous flame that
narrows towards the top. Tongues of flame also curl up the sides, with a darker crease where each one meets
the body of the fire.

- The N is always fully intact and white. The flames are drawn around and above it, never over it.
  `tests/test_branding.py` checks this pixel by pixel, so a later edit cannot quietly damage the letter.
- It is drawn on a 64 x 64 pixel grid using only plain rectangles (no fonts, scripts or outside references),
  so it renders the same everywhere and is safe to ship. It stays readable down to about 24 px.
- The dark badge keeps the white N visible on both light and dark backgrounds.
- The art is original and is the project's own (no Fedora artwork is used).

## Where it will be used

The Start button (Kickoff launcher), the login and boot screens, `/etc/os-release` (`LOGO=`), the About page
and the GitHub page. Sizes come from the SVG, for example on Fedora with librsvg:

```
rsvg-convert -w 256 -h 256 branding/normie-logo.svg -o normie-logo-256.png
```

## Changing it

Edit the SVG, keep the N group (`<g fill="#ffffff">`) exactly as it is, run the tests
(`python3 -m unittest discover -s tests`), and look at the result at 22, 48 and 256 px before committing.
