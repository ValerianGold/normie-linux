import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


class DistList(unittest.TestCase):
    def test_list_is_up_to_date(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "export-deps.py"), "--check"])
        self.assertEqual(r.returncode, 0, "dist/normie-deps.list is stale: run tools/export-deps.py")

    def test_every_line_passes_the_clients_name_filter(self):
        # the same rule normie-update applies; a name that fails would be silently ignored
        rule = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}$")
        with open(os.path.join(ROOT, "dist", "normie-deps.list")) as fh:
            for line in fh:
                line = line.split("#")[0].strip()
                if line:
                    self.assertRegex(line, rule)


if __name__ == "__main__":
    unittest.main()
