"""Tests for the GitHub helper script and the GitHub-facing files. Nothing here touches the network."""
import atexit
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPT = os.path.join(ROOT, "tools", "set-github-user.sh")

try:
    import yaml
except ImportError:                      # the CI runner usually has it; skip rather than fail
    yaml = None


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def read(path):
    with open(path) as fh:
        return fh.read()


class SetGithubUser(unittest.TestCase):
    def make_tree(self):
        d = tempfile.mkdtemp(prefix="normie-gh-")
        atexit.register(shutil.rmtree, d, True)
        os.makedirs(f"{d}/tools")
        shutil.copy(SCRIPT, f"{d}/tools/set-github-user.sh")
        write(f"{d}/root/etc/normie/update.conf", '# comment\nDEPS_LIST_URL=""\nFIRMWARE="no"\n')
        write(f"{d}/Normie-Linux.kiwi", "<image><description><contact>TODO-set</contact></description></image>\n")
        return d

    def run_script(self, d, *args):
        return subprocess.run(["bash", f"{d}/tools/set-github-user.sh", *args], capture_output=True, text=True)

    def test_sets_list_address_and_contact(self):
        d = self.make_tree()
        r = self.run_script(d, "valerian-example")
        self.assertEqual(r.returncode, 0, r.stderr)
        conf = read(f"{d}/root/etc/normie/update.conf")
        self.assertIn('DEPS_LIST_URL="https://raw.githubusercontent.com/valerian-example/normie-linux/main/dist/normie-deps.list"', conf)
        self.assertIn('FIRMWARE="no"', conf)                      # other settings untouched
        self.assertIn("<contact>https://github.com/valerian-example/normie-linux</contact>", read(f"{d}/Normie-Linux.kiwi"))

    def test_custom_repo_name_and_rerun(self):
        d = self.make_tree()
        self.run_script(d, "someone", "my-distro")
        self.run_script(d, "someone", "my-distro")
        conf = read(f"{d}/root/etc/normie/update.conf")
        self.assertEqual(conf.count("DEPS_LIST_URL="), 1)
        self.assertIn("/someone/my-distro/main/", conf)

    def test_bad_input_changes_nothing(self):
        for bad in ("", "has space", "--help", "a;b", "$(x)", "-leading", "trailing-", "x" * 40):
            d = self.make_tree()
            before = read(f"{d}/root/etc/normie/update.conf"), read(f"{d}/Normie-Linux.kiwi")
            r = self.run_script(d, bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertEqual((read(f"{d}/root/etc/normie/update.conf"), read(f"{d}/Normie-Linux.kiwi")), before, bad)

    def test_bad_repo_name_changes_nothing(self):
        d = self.make_tree()
        before = read(f"{d}/root/etc/normie/update.conf")
        self.assertEqual(self.run_script(d, "someone", "bad/repo").returncode, 2)
        self.assertEqual(read(f"{d}/root/etc/normie/update.conf"), before)

    def test_the_url_it_writes_passes_the_clients_own_url_rule(self):
        # normie-update only accepts https:// and normie-remind extracts it with a pattern; use the real pattern
        d = self.make_tree()
        self.run_script(d, "valerian-example")
        remind = read(os.path.join(ROOT, "root", "usr", "libexec", "normie", "normie-remind"))
        self.assertIn('https://', remind)
        out = subprocess.run(
            ["sed", "-n", 's#^DEPS_LIST_URL="\\{0,1\\}\\(https://[^"[:space:]]*\\)"\\{0,1\\}[[:space:]]*$#\\1#p',
             f"{d}/root/etc/normie/update.conf"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "https://raw.githubusercontent.com/valerian-example/normie-linux/main/dist/normie-deps.list")


@unittest.skipIf(yaml is None, "PyYAML not installed")
class GithubFiles(unittest.TestCase):
    def load(self, rel):
        with open(os.path.join(ROOT, rel)) as fh:
            return yaml.safe_load(fh)

    def test_workflow_runs_the_tests_and_checks(self):
        wf = self.load(".github/workflows/tests.yml")
        triggers = wf.get("on", wf.get(True))            # PyYAML reads the bare word `on` as True
        self.assertIn("push", triggers)
        text = read(os.path.join(ROOT, ".github/workflows/tests.yml"))
        for needle in ("unittest discover", "validate-kiwi.py", "export-deps.py --check"):
            self.assertIn(needle, text)

    def test_issue_forms_are_valid_and_complete(self):
        for rel in (".github/ISSUE_TEMPLATE/missing-dependency.yml", ".github/ISSUE_TEMPLATE/bug_report.yml"):
            doc = self.load(rel)
            self.assertTrue(doc["name"] and doc["description"], rel)
            ids = [b["id"] for b in doc["body"] if "id" in b]
            self.assertEqual(len(ids), len(set(ids)), rel)
            for b in doc["body"]:
                self.assertIn(b["type"], ("markdown", "input", "textarea", "dropdown", "checkboxes"))
        dropdown = [b for b in self.load(".github/ISSUE_TEMPLATE/missing-dependency.yml")["body"] if b["type"] == "dropdown"][0]
        self.assertGreaterEqual(len(dropdown["attributes"]["options"]), 3)


# Files allowed to match, each for a stated reason:
#   this file                   lists the patterns it searches for
#   components/users.xml        Fedora's placeholder build password; config.sh runs `passwd -d root` and
#                               `passwd -l root`, so it never ships (verified when this test was written)
#   teams/cloud/vagrant.xml     Fedora's own Vagrant cloud image; Normie Linux does not build it
KNOWN_UPSTREAM_OR_SELF = {"tests/test_github_files.py", "components/users.xml", "teams/cloud/vagrant.xml"}


class NoLeftovers(unittest.TestCase):
    def test_no_secrets_or_personal_paths_are_committed(self):
        suspicious = ("BEGIN PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY", "ghp_", "github_pat_", "/home/valerian", "password=")
        skip = {".git", "__pycache__"}
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [x for x in dirs if x not in skip]
            for name in files:
                path = os.path.join(base, name)
                if os.path.islink(path) or os.path.getsize(path) > 2_000_000:
                    continue
                try:
                    text = read(path)
                except (UnicodeDecodeError, OSError):
                    continue
                if os.path.relpath(path, ROOT) in KNOWN_UPSTREAM_OR_SELF:
                    continue
                for s in suspicious:
                    self.assertNotIn(s, text, f"{s!r} found in {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    unittest.main()
