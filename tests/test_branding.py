"""The logo must stay a safe, self-contained image (no fonts, scripts or external references),
and the letter N must stay fully intact and white, with the fire only ever drawn outside it."""
import os
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO = os.path.join(ROOT, "branding", "normie-logo.svg")
SVG = "{http://www.w3.org/2000/svg}"
FLAME_COLOURS = {"#ffe85c", "#ffc933", "#ffa326", "#f77a1d", "#dc4c17", "#a92a14"}   # hottest to coolest


def n_cells():
    """The N on the 64x64 pixel grid: two 8-wide stems, 26 rows tall, joined by a 10-wide diagonal."""
    c0, r0, rows, stem, diag = 15, 32, 26, 8, 10
    right = c0 + rows - 1
    cells = set()
    for r in range(r0, r0 + rows):
        for c in range(c0, c0 + stem):
            cells.add((c, r))
        for c in range(right, right + stem):
            cells.add((c, r))
        s = c0 + (r - r0)
        for c in range(s, s + diag):
            if c <= right + stem - 1:
                cells.add((c, r))
    return cells


def cells_of(group):
    cells = set()
    for rect in group:
        x, y, w, h = (int(rect.get(k)) for k in ("x", "y", "width", "height"))
        for dx in range(w):
            for dy in range(h):
                cells.add((x + dx, y + dy))
    return cells


class Logo(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(LOGO).getroot()
        self.groups = [g for g in self.root.iter(SVG + "g")]

    def white_group(self):
        group = [g for g in self.groups if g.get("fill") == "#ffffff"]
        self.assertEqual(len(group), 1)
        return group[0]

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

    def test_the_n_is_exactly_the_whole_letter_and_white(self):
        group = self.white_group()
        self.assertTrue(all(r.tag == SVG + "rect" for r in group))
        self.assertEqual(cells_of(group), n_cells())

    def test_the_fire_never_touches_the_letter(self):
        n = n_cells()
        flames = [g for g in self.groups if g.get("fill") in FLAME_COLOURS]
        self.assertTrue(flames)
        fire = set()
        for g in flames:
            cells = cells_of(g)
            self.assertFalse(cells & n, "flame pixels overlap the N")
            self.assertFalse(cells & fire, "two flame colours overlap")
            fire |= cells
        # the fire really is on top: it rises above the top of the N
        self.assertLess(min(r for _, r in fire), min(r for _, r in n) - 12)

    def test_everything_stays_inside_the_canvas(self):
        for g in self.groups:
            for c, r in cells_of(g):
                self.assertTrue(0 <= c < 64 and 0 <= r < 64, (c, r))

    def test_no_other_group_draws_white(self):
        for g in self.groups:
            if g.get("fill") != "#ffffff":
                self.assertIn(g.get("fill"), FLAME_COLOURS)


if __name__ == "__main__":
    unittest.main()
