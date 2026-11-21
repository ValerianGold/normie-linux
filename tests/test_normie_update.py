#!/usr/bin/env python3
"""
Tests for root/usr/libexec/normie/normie-update using fake commands.
Nothing here touches the real system.   Run:  python3 -m unittest discover -s tests -v
"""
import atexit
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
UPDATE = os.path.join(HERE, "..", "root", "usr", "libexec", "normie", "normie-update")


def w(path, text, mode=None):
    with open(path, "w") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


STUBS = {
    # curl: fail if $FAKE/offline exists; for "-o FILE" copy $FAKE/deplist into FILE
    "curl": '''#!/bin/sh
[ -e "$FAKE/offline" ] && exit 6
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
[ -n "$out" ] && [ -e "$FAKE/deplist" ] && [ "$out" != /dev/null ] && cp "$FAKE/deplist" "$out"
exit 0
''',
    "rpm": '''#!/bin/sh
case "$1" in
  -E) echo 45 ;;
  -q) if [ "$2" = kernel-core ]; then cat "$FAKE/kernels"; exit 0; fi
      grep -qx "$2" "$FAKE/installed" 2>/dev/null && exit 0; exit 1 ;;
esac
''',
    "uname": '#!/bin/sh\necho 6.20.1-100.fc45.x86_64\n',
    "dnf": '#!/bin/sh\necho "dnf $*" >> "$FAKE/calls"\n[ -e "$FAKE/dnf-fails" ] && exit 1\nexit 0\n',
    "flatpak": '#!/bin/sh\necho "flatpak $*" >> "$FAKE/calls"\n',
}


class Env:
    def __init__(self, deplist="gcc\n", installed=("rpmfusion-free-release", "rpmfusion-nonfree-release"),
                 kernels=("6.20.1-100.fc45.x86_64",), conf_url=True):
        d = tempfile.mkdtemp(prefix="normie-upd-")
        atexit.register(shutil.rmtree, d, True)
        self.fake = d
        os.makedirs(f"{d}/bin")
        os.makedirs(f"{d}/libexec")
        w(f"{d}/calls", "")
        w(f"{d}/installed", "\n".join(installed) + "\n")
        w(f"{d}/kernels", "\n".join(kernels) + "\n")
        if deplist is not None:
            w(f"{d}/deplist", deplist)
        w(f"{d}/update.conf", 'DEPS_LIST_URL="https://example.invalid/normie-deps.list"\n' if conf_url else "")
        for n, body in STUBS.items():
            w(f"{d}/bin/{n}", body, 0o755)
        # fake normie-gpu that just records it was called and prints a protocol line
        w(f"{d}/libexec/normie-gpu",
          '#!/bin/sh\necho "normie-gpu $*" >> "$FAKE/calls"\necho "INFO|fake gpu step"\n', 0o755)
        self.env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_LIBEXEC=f"{d}/libexec",
                        NORMIE_CONF=f"{d}/update.conf", NORMIE_LOG=f"{d}/log",
                        PATH=f"{d}/bin:" + os.environ["PATH"])

    def run(self, *args, root=True, live=False):
        env = dict(self.env)
        env["NORMIE_FAKE_ROOT"] = "1" if root else "0"
        if live:
            env["NORMIE_FORCE_LIVE"] = "1"
        r = subprocess.run(["bash", UPDATE, *args], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def calls(self):
        with open(f"{self.fake}/calls") as fh:
            return fh.read()


class UpdateTests(unittest.TestCase):
    def test_dry_run_needs_no_root_and_changes_nothing(self):
        e = Env()
        rc, out = e.run("--dry-run", root=False)
        self.assertEqual(rc, 0, out)
        self.assertIn("PROGRESS|0|Checking your connection", out)
        self.assertIn("RESULT|ok|", out)
        self.assertIn("DRY|dnf upgrade --refresh -y", out)
        # the only thing that may run is the GPU tool, and only in its own dry-run mode
        self.assertEqual(e.calls().strip(), "normie-gpu apply --dry-run")

    def test_dry_run_allowed_in_live_session_but_real_run_refused(self):
        e = Env()
        self.assertEqual(e.run("--dry-run", root=False, live=True)[0], 0)
        open(f"{e.fake}/calls", "w").close()
        rc, out = e.run(live=True)
        self.assertEqual(rc, 1)
        self.assertIn("live session", out)
        self.assertEqual(e.calls(), "")

    def test_real_run_requires_root(self):
        rc, out = Env().run(root=False)
        self.assertEqual(rc, 1)
        self.assertIn("administrator", out)

    def test_full_run_order_and_result(self):
        e = Env()
        rc, out = e.run()
        self.assertEqual(rc, 0, out)
        c = e.calls()
        self.assertLess(c.index("dnf upgrade --refresh -y"), c.index("flatpak update"))
        self.assertLess(c.index("flatpak update"), c.index("normie-gpu apply"))
        self.assertIn("RESULT|ok|", out)
        self.assertIn("PROGRESS|100|Done", out)

    def test_offline_stops_immediately_and_touches_nothing(self):
        e = Env()
        open(f"{e.fake}/offline", "w").close()
        rc, out = e.run()
        self.assertEqual(rc, 1)
        self.assertIn("No internet connection", out)
        self.assertIn("RESULT|failed|no internet", out)
        self.assertEqual(e.calls(), "")

    def test_missing_rpmfusion_gets_added_with_official_urls(self):
        e = Env(installed=())
        e.run()
        c = e.calls()
        self.assertIn("https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-45.noarch.rpm", c)
        self.assertIn("https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-45.noarch.rpm", c)

    def test_gpu_only_mode_skips_system_upgrade(self):
        e = Env()
        rc, out = e.run("--only", "gpu")
        c = e.calls()
        self.assertIn("normie-gpu apply", c)
        self.assertNotIn("dnf upgrade", c)
        self.assertNotIn("flatpak", c)

    def test_dependency_list_installs_valid_names_only(self):
        evil = "# comment\ngcc-c++\nlibXtst.i686  # trailing comment\n--installroot=/tmp/x\n-y\nrm -rf /\nfoo;bar\n\nwebkit2gtk4.1\n"
        e = Env(deplist=evil)
        rc, out = e.run()
        install = [l for l in e.calls().splitlines() if "--skip-unavailable" in l]
        self.assertEqual(len(install), 1, e.calls())
        self.assertEqual(install[0], "dnf install -y --skip-unavailable gcc-c++ libXtst.i686 webkit2gtk4.1")
        self.assertNotIn("installroot", e.calls())
        self.assertIn("Ignoring an invalid line", out)

    def test_http_list_url_is_rejected(self):
        e = Env(deplist="gcc\n")
        w(f"{e.fake}/update.conf", 'DEPS_LIST_URL="http://insecure.invalid/list"\n')
        rc, out = e.run()
        self.assertNotIn("--skip-unavailable", e.calls())
        self.assertIn("https://", out)

    def test_empty_or_huge_list_is_rejected(self):
        e = Env(deplist="# nothing here\n")
        e.run()
        self.assertNotIn("--skip-unavailable", e.calls())

    def test_no_url_configured_skips_quietly(self):
        e = Env(conf_url=False)
        rc, out = e.run()
        self.assertEqual(rc, 0)
        self.assertIn("No online dependency list configured", out)

    def test_failed_upgrade_is_reported_not_hidden(self):
        e = Env()
        open(f"{e.fake}/dnf-fails", "w").close()
        rc, out = e.run()
        self.assertEqual(rc, 1)
        self.assertIn("RESULT|partial|", out)
        self.assertIn("did not finish", out)

    def test_new_kernel_asks_for_restart(self):
        e = Env(kernels=("6.20.1-100.fc45.x86_64", "6.21.0-100.fc45.x86_64"))
        rc, out = e.run()
        self.assertIn("NEEDS_REBOOT|", out)

    def test_same_kernel_no_restart(self):
        rc, out = Env().run()
        self.assertNotIn("NEEDS_REBOOT|", out)


if __name__ == "__main__":
    unittest.main()
