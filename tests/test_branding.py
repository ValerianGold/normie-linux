"""The logo must stay a safe, self-contained image: no fonts, scripts, or external references."""
import os
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO = os.path.join(ROOT, "branding", "normie-logo.svg")
SVG = "{http://www.w3.org/2000/svg}"


class Logo(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(LOGO).getroot()

    def test_is_a_square_svg_with_a_title(self):
        self.assertEqual(self.root.tag, SVG + "svg")
        x, y, w, h = [float(v) for v in self.root.get("viewBox").split()]
        self.assertEqual((x, y), (0, 0))
        self.assertEqual(w, h)
        self.assertTrue(self.root.find(SVG + "title") is not None)

    def test_only_plain_shapes_are_used(self):
        allowed = {"svg", "title", "defs", "linearGradient", "stop", "rect", "g", "polygon", "path"}
        for el in self.root.iter():
            self.assertIn(el.tag.replace(SVG, ""), allowed, el.tag)

    def test_no_text_fonts_scripts_or_external_references(self):
        with open(LOGO) as fh:
            text = fh.read().lower()
        for bad in ("<text", "font-", "<script", "<image", "href", "http://www.w3.org/1999/xlink",
                    "javascript:", "<foreignobject", "onload", "@import", "url(http"):
            self.assertNotIn(bad, text, bad)

    def test_every_gradient_that_is_used_is_defined(self):
        defined = {g.get("id") for g in self.root.iter(SVG + "linearGradient")}
        used = set()
        for el in self.root.iter():
            f = el.get("fill", "")
            if f.startswith("url(#"):
                used.add(f[5:-1])
        self.assertTrue(used)
        self.assertLessEqual(used, defined)

    def test_the_n_is_white_and_inside_the_canvas(self):
        group = [g for g in self.root.iter(SVG + "g") if g.get("fill") == "#ffffff"]
        self.assertEqual(len(group), 1)
        self.assertEqual(len(list(group[0])), 3)          # two stems and the diagonal


if __name__ == "__main__":
    unittest.main()
