import datetime
import difflib
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BumpPackage(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        os.makedirs(self.d + "/tools")
        shutil.copy(ROOT + "/tools/bump-package.sh", self.d + "/tools/")
        shutil.copytree(ROOT + "/packaging", self.d + "/packaging", symlinks=True)

    def run_tool(self, *args):
        r = subprocess.run(["bash", self.d + "/tools/bump-package.sh", *args], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def spec(self, name):
        with open(f"{self.d}/packaging/{name}/{name}.spec", encoding="utf-8") as fh:
            return fh.read()

    def test_it_raises_the_release_and_adds_a_dated_changelog_line(self):
        before = self.spec("normie-logos")
        old = int(re.search(r"^Release:\s+(\d+)%\{\?dist\}", before, re.M).group(1))
        rc, out = self.run_tool("normie-logos", "New logo")
        self.assertEqual(rc, 0, out)
        after = self.spec("normie-logos")
        self.assertRegex(after, rf"(?m)^Release:\s+{old + 1}%\{{\?dist\}}$")
        top = after.split("%changelog\n", 1)[1].splitlines()
        m = re.match(r"^\* (\w{3}) (\w{3}) (\d+) (\d{4}) Normie Linux contributors <noreply@invalid> - 0\.1-(\d+)$", top[0])
        self.assertTrue(m, top[0])
        self.assertEqual(int(m.group(5)), old + 1)
        d = datetime.datetime.strptime(f"{m.group(2)} {m.group(3)} {m.group(4)}", "%b %d %Y")
        self.assertEqual(d.strftime("%a"), m.group(1))
        self.assertEqual(top[1], "- New logo")
        self.assertIn("- First release", after)                  # the older entry is still there

    def test_nothing_else_in_the_spec_changes(self):
        before = self.spec("normie-logos").splitlines()
        self.run_tool("normie-logos", "x")
        after = self.spec("normie-logos").splitlines()
        self.assertEqual(len(after), len(before) + 2)
        diff = [l for l in difflib.unified_diff(before, after, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        added = [l for l in diff if l[0] == "+"]
        removed = [l for l in diff if l[0] == "-"]
        self.assertEqual(len(removed), 1)                        # the old Release line
        self.assertEqual(len(added), 3)                          # the new Release line, the dated line, the note
        self.assertTrue(removed[0].startswith("-Release:"))

    def test_two_runs_count_up(self):
        # start from whatever the real spec says: the maintainer raises it for real, so it is not always 1
        start = int(re.search(r"(?m)^Release:\s+(\d+)%\{\?dist\}", self.spec("normie-logos")).group(1))
        self.run_tool("normie-logos", "one")
        self.run_tool("normie-logos", "two")
        self.assertRegex(self.spec("normie-logos"), rf"(?m)^Release:\s+{start + 2}%\{{\?dist\}}$")

    def test_versions_that_come_from_a_macro_are_written_out(self):
        for name, ver in (("normie-tools", "0.1"), ("normie-release", "45")):
            start = int(re.search(r"(?m)^Release:\s+(\d+)%\{\?dist\}", self.spec(name)).group(1))
            rc, out = self.run_tool(name, "Fix")
            self.assertEqual(rc, 0, out)
            self.assertRegex(self.spec(name), rf"(?m)^\* .* - {re.escape(ver)}-{start + 1}$")

    def test_bad_input_changes_nothing(self):
        snapshot = {n: self.spec(n) for n in ("normie-logos", "normie-tools")}
        for args in ((), ("normie-logos",), ("normie-logos", ""), ("../x", "y"), ("no-such", "y"),
                     ("normie-logos", "two\nlines")):
            rc, _ = self.run_tool(*args)
            self.assertNotEqual(rc, 0, args)
        for n, text in snapshot.items():
            self.assertEqual(self.spec(n), text)

    def test_the_specs_still_pass_the_changelog_rules_afterwards(self):
        for n in ("normie-logos", "normie-backgrounds-kde", "normie-lookandfeel", "normie-release", "normie-tools"):
            rc, out = self.run_tool(n, "Test")
            self.assertEqual(rc, 0, out)
            for l in [l for l in self.spec(n).split("%changelog\n", 1)[1].splitlines() if l.startswith("*")]:
                m = re.match(r"^\* (\w{3}) (\w{3}) (\d+) (\d{4}) ", l)
                self.assertTrue(m, l)
                d = datetime.datetime.strptime(f"{m.group(2)} {m.group(3)} {m.group(4)}", "%b %d %Y")
                self.assertEqual(d.strftime("%a"), m.group(1), l)


if __name__ == "__main__":
    unittest.main()
