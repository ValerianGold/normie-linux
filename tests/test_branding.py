"""The logo must stay a safe, self-contained image: square, no fonts, scripts or external references.

These rules hold for any logo, so the design can change without touching the tests. (Earlier tests checked the
pixels of a particular design; they were replaced when the logo was redrawn.)"""
import os
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO = os.path.join(ROOT, "branding", "normie-logo.svg")
SVG = "{http://www.w3.org/2000/svg}"
SHAPES = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}
ALLOWED = SHAPES | {"svg", "g", "defs", "title", "desc", "style", "linearGradient", "radialGradient", "stop", "clipPath"}


def number(value):
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*(px)?\s*$", value or "")
    return float(m.group(1)) if m else None


class Logo(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(LOGO).getroot()
        with open(LOGO, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_is_an_svg_with_something_drawn(self):
        self.assertEqual(self.root.tag, SVG + "svg")
        self.assertTrue([el for el in self.root.iter() if el.tag.replace(SVG, "") in SHAPES])

    def test_is_square_so_the_icons_are_not_stretched(self):
        parts = re.split(r"[\s,]+", (self.root.get("viewBox") or "").strip())
        self.assertEqual(len(parts), 4, "the SVG needs a viewBox")
        w, h = float(parts[2]), float(parts[3])
        self.assertGreater(w, 0)
        self.assertAlmostEqual(w, h, delta=0.01, msg=f"the viewBox is {w} by {h}; make it square (add empty margin)")
        sw, sh = number(self.root.get("width")), number(self.root.get("height"))
        if sw is not None and sh is not None:
            self.assertAlmostEqual(sw, sh, delta=0.01)

    def test_only_plain_drawing_elements_are_used(self):
        for el in self.root.iter():
            self.assertIn(el.tag.replace(SVG, ""), ALLOWED, el.tag)

    def test_no_text_fonts_scripts_or_external_references(self):
        low = self.text.lower()
        for bad in ("<text", "font-", "<script", "<image", "href", "javascript:", "<foreignobject",
                    "onload", "@import", "url(http", "<!entity", "<use"):
            self.assertNotIn(bad, low, bad)

    def test_every_gradient_or_clip_that_is_used_is_defined(self):
        defined = {el.get("id") for el in self.root.iter() if el.get("id")}
        for ref in re.findall(r"url\(\s*#([^)\s]+)\s*\)", self.text):
            self.assertIn(ref, defined, f"url(#{ref}) points at nothing")

    def test_is_small_enough_to_ship_everywhere(self):
        self.assertLess(os.path.getsize(LOGO), 200 * 1024)


if __name__ == "__main__":
    unittest.main()
