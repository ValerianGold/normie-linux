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
    "fwupdmgr": '#!/bin/sh\necho "fwupdmgr $*" >> "$FAKE/calls"\n[ -e "$FAKE/fwupd-rc" ] && exit "$(cat "$FAKE/fwupd-rc")"\nexit 0\n',
}


class Env:
    def __init__(self, deplist="gcc\n", installed=("rpmfusion-free-release", "rpmfusion-nonfree-release"),
                 kernels=("6.20.1-100.fc45.x86_64",), conf_url=True, firmware=None, power=None):
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
        conf = 'DEPS_LIST_URL="https://example.invalid/normie-deps.list"\n' if conf_url else ""
        if firmware:
            conf += f'FIRMWARE="{firmware}"\n'
        w(f"{d}/update.conf", conf)
        os.makedirs(f"{d}/power")
        for name, (typ, online) in (power or {}).items():
            os.makedirs(f"{d}/power/{name}")
            w(f"{d}/power/{name}/type", typ + "\n")
            if online is not None:
                w(f"{d}/power/{name}/online", f"{online}\n")
        for n, body in STUBS.items():
            w(f"{d}/bin/{n}", body, 0o755)
        # fake normie-gpu that just records it was called and prints a protocol line
        w(f"{d}/libexec/normie-gpu",
          '#!/bin/sh\necho "normie-gpu $*" >> "$FAKE/calls"\necho "INFO|fake gpu step"\n', 0o755)
        self.env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_LIBEXEC=f"{d}/libexec",
                        NORMIE_CONF=f"{d}/update.conf", NORMIE_LOG=f"{d}/log", NORMIE_POWER=f"{d}/power",
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

    # ---- Flathub and firmware
    def test_button_makes_sure_flathub_is_configured_before_updating_apps(self):
        e = Env()
        e.run()
        c = e.calls()
        self.assertIn("flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo", c)
        self.assertLess(c.index("remote-add"), c.index("flatpak update"))

    def test_firmware_is_off_by_default(self):
        e = Env()
        rc, out = e.run()
        self.assertNotIn("fwupdmgr", e.calls())
        self.assertIn("Firmware updates are off", out)

    def test_firmware_on_runs_refresh_then_update(self):
        e = Env(firmware="yes")
        rc, out = e.run()
        c = e.calls()
        self.assertEqual(rc, 0, out)
        self.assertLess(c.index("fwupdmgr refresh"), c.index("fwupdmgr update -y --no-reboot-check"))
        self.assertIn("applied during the next restart", out)

    def test_firmware_skipped_on_battery(self):
        e = Env(firmware="yes", power={"AC": ("Mains", 0), "BAT0": ("Battery", None)})
        rc, out = e.run()
        self.assertNotIn("fwupdmgr", e.calls())
        self.assertIn("battery", out)

    def test_firmware_runs_when_plugged_in(self):
        e = Env(firmware="yes", power={"AC": ("Mains", 1), "BAT0": ("Battery", None)})
        e.run()
        self.assertIn("fwupdmgr update", e.calls())

    def test_firmware_nothing_to_update_is_not_an_error(self):
        e = Env(firmware="yes")
        w(f"{e.fake}/fwupd-rc", "2\n")
        rc, out = e.run()
        self.assertEqual(rc, 0, out)
        self.assertIn("RESULT|ok|", out)

    def test_firmware_real_failure_is_reported(self):
        e = Env(firmware="yes")
        w(f"{e.fake}/fwupd-rc", "1\n")
        rc, out = e.run()
        self.assertEqual(rc, 1)
        self.assertIn("RESULT|partial|", out)

    def test_firmware_step_not_in_gpu_only_mode(self):
        e = Env(firmware="yes")
        e.run("--only", "gpu")
        self.assertNotIn("fwupdmgr", e.calls())


class FlathubScript(unittest.TestCase):
    SCRIPT = os.path.join(HERE, "..", "root", "usr", "libexec", "normie", "normie-flathub")

    def make(self, remotes="", fail=False):
        d = tempfile.mkdtemp(prefix="normie-fh-")
        atexit.register(shutil.rmtree, d, True)
        os.makedirs(f"{d}/bin")
        w(f"{d}/bin/flatpak", """#!/bin/sh
case "$1" in
  remotes) printf '%s' "$REMOTES" ;;
  remote-add) echo "flatpak $*" >> "$FAKE/calls"; [ -n "$FAIL" ] && exit 1; exit 0 ;;
esac
""", 0o755)
        w(f"{d}/calls", "")
        env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_STATE=f"{d}/state", REMOTES=remotes,
                   FAIL="1" if fail else "", PATH=f"{d}/bin:" + os.environ["PATH"])
        return d, env

    def run_script(self, env):
        r = subprocess.run(["bash", self.SCRIPT], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_adds_flathub_and_records_success(self):
        d, env = self.make()
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)
        with open(f"{d}/calls") as fh:
            self.assertIn("remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo", fh.read())
        self.assertTrue(os.path.exists(f"{d}/state/flathub-done"))

    def test_already_present_does_nothing_but_records_success(self):
        d, env = self.make(remotes="flathub\n")
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0)
        with open(f"{d}/calls") as fh:
            self.assertEqual(fh.read(), "")
        self.assertTrue(os.path.exists(f"{d}/state/flathub-done"))

    def test_offline_fails_without_recording_success_so_it_retries_next_boot(self):
        d, env = self.make(fail=True)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(f"{d}/state/flathub-done"))
        with open(f"{d}/calls") as fh:
            self.assertEqual(len(fh.read().splitlines()), 6)      # retried six times

    def test_service_is_enabled_and_cannot_block_the_login_screen(self):
        root = os.path.join(HERE, "..", "root")
        link = os.path.join(root, "etc/systemd/system/multi-user.target.wants/normie-flathub.service")
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.readlink(link), "/usr/lib/systemd/system/normie-flathub.service")
        with open(os.path.join(root, "usr/lib/systemd/system/normie-flathub.service")) as fh:
            unit = fh.read()
        self.assertIn("Type=simple", unit)
        self.assertIn("ConditionPathExists=!/var/lib/normie/flathub-done", unit)


if __name__ == "__main__":
    unittest.main()
