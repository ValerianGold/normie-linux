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
LIB = os.path.abspath(os.path.join(HERE, "..", "root", "usr", "libexec", "normie", "normie-lib.sh"))


def names_hash(names):
    """The fingerprint normie-lib.sh computes: sorted, de-duplicated names, one per line."""
    import hashlib
    return hashlib.sha256(("\n".join(sorted(set(names))) + "\n").encode()).hexdigest()


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
        os.symlink(LIB, f"{d}/libexec/normie-lib.sh")
        w(f"{d}/libexec/normie-sources",
          '#!/bin/sh\necho "normie-sources $*" >> "$FAKE/calls"\n[ -e "$FAKE/sources-fails" ] && exit 1\necho "Software sources are ready"\n', 0o755)
        self.env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_LIBEXEC=f"{d}/libexec", NORMIE_STATE=f"{d}/state",
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
        # the only things that may run are our own helpers, each in its own dry-run mode
        self.assertEqual(e.calls().strip().splitlines(),
                         ["normie-sources --dry-run", "normie-gpu apply --dry-run"])

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

    def test_button_runs_the_sources_setup_before_updating(self):
        e = Env()
        e.run()
        c = e.calls()
        self.assertIn("normie-sources", c)
        self.assertLess(c.index("normie-sources"), c.index("dnf upgrade"))

    def test_sources_failure_is_reported_but_update_continues(self):
        e = Env()
        open(f"{e.fake}/sources-fails", "w").close()
        rc, out = e.run()
        self.assertIn("dnf upgrade --refresh -y", e.calls())
        self.assertIn("RESULT|partial|", out)
        self.assertIn("software sources could not be set up", out)

    def test_dry_run_passes_dry_run_to_sources(self):
        e = Env()
        e.run("--dry-run", root=False)
        self.assertIn("normie-sources --dry-run", e.calls())

    # ---- last-updated stamp (feeds the reminder)
    def test_success_writes_last_update_stamp(self):
        e = Env()
        rc, out = e.run()
        self.assertEqual(rc, 0, out)
        with open(f"{e.fake}/state/last-update") as fh:
            self.assertRegex(fh.read().strip(), r"^\d{10}$")

    def test_failure_or_dry_run_or_gpu_only_do_not_write_stamp(self):
        e = Env()
        open(f"{e.fake}/dnf-fails", "w").close()
        e.run()
        self.assertFalse(os.path.exists(f"{e.fake}/state/last-update"))
        e2 = Env()
        e2.run("--dry-run", root=False)
        e2.run("--only", "gpu")
        self.assertFalse(os.path.exists(f"{e2.fake}/state/last-update"))

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
        self.assertIn("invalid line", out)

    def test_applied_list_version_is_remembered(self):
        e = Env(deplist="webkit2gtk4.1\ngcc-c++  # comment\n\ngcc-c++\n")
        rc, out = e.run()
        with open(f"{e.fake}/state/deps-applied") as fh:
            self.assertEqual(fh.read().strip(), names_hash(["gcc-c++", "webkit2gtk4.1"]))

    def test_list_version_not_remembered_when_install_fails(self):
        e = Env(deplist="gcc\n")
        open(f"{e.fake}/dnf-fails", "w").close()
        e.run()
        self.assertFalse(os.path.exists(f"{e.fake}/state/deps-applied"))

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


class SourcesScript(unittest.TestCase):
    SCRIPT = os.path.join(HERE, "..", "root", "usr", "libexec", "normie", "normie-sources")

    def make(self, remotes="", installed=(), dnf_fails=False, flatpak_fails=False, have_flatpak=True,
             beta_fails=False, conf="", third_party=None, third_party_fails=False):
        d = tempfile.mkdtemp(prefix="normie-src-")
        atexit.register(shutil.rmtree, d, True)
        os.makedirs(f"{d}/bin")
        w(f"{d}/calls", "")
        w(f"{d}/installed", "\n".join(installed) + "\n")
        if have_flatpak:
            w(f"{d}/bin/flatpak", """#!/bin/sh
case "$1" in
  remotes) printf '%s' "$REMOTES" ;;
  remote-add) echo "flatpak $*" >> "$FAKE/calls"; [ -n "$FLATPAK_FAILS" ] && exit 1
              case "$*" in *beta*) [ -n "$BETA_FAILS" ] && exit 1 ;; esac; exit 0 ;;
esac
""", 0o755)
        w(f"{d}/conf", conf)
        if third_party is not None:       # None = tool not installed; otherwise the text `query` prints
            w(f"{d}/tp-state", third_party + "\n")
            w(f"{d}/bin/fedora-third-party", """#!/bin/sh
case "$1" in
  query) cat "$FAKE/tp-state" ;;
  enable) echo "fedora-third-party enable" >> "$FAKE/calls"; [ -n "$TP_FAILS" ] && exit 1; exit 0 ;;
esac
""", 0o755)
        w(f"{d}/bin/rpm", """#!/bin/sh
case "$1" in
  -E) echo 45 ;;
  -q) grep -qx "$2" "$FAKE/installed" && exit 0; exit 1 ;;
esac
""", 0o755)
        w(f"{d}/bin/dnf", '#!/bin/sh\necho "dnf $*" >> "$FAKE/calls"\n[ -n "$DNF_FAILS" ] && exit 1\nexit 0\n', 0o755)
        # a PATH with only our stubs plus the basics, so "no flatpak" is really "no flatpak"
        for tool in ("bash", "sh", "grep", "seq", "sleep", "mkdir", "touch", "cat", "env"):
            src = shutil.which(tool)
            if src and not os.path.exists(f"{d}/bin/{tool}"):
                os.symlink(src, f"{d}/bin/{tool}")
        env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_STATE=f"{d}/state", REMOTES=remotes,
                   DNF_FAILS="1" if dnf_fails else "", FLATPAK_FAILS="1" if flatpak_fails else "",
                   BETA_FAILS="1" if beta_fails else "", TP_FAILS="1" if third_party_fails else "",
                   NORMIE_CONF=f"{d}/conf", PATH=f"{d}/bin")
        return d, env

    def run_script(self, env, *args):
        r = subprocess.run(["bash", self.SCRIPT, *args], env=env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def calls(self, d):
        with open(f"{d}/calls") as fh:
            return fh.read()

    def test_fresh_system_gets_everything_and_records_success(self):
        d, env = self.make()
        rc, out = self.run_script(env)
        c = self.calls(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo", c)
        self.assertIn("rpmfusion-free-release-45.noarch.rpm", c)
        self.assertIn("rpmfusion-nonfree-release-45.noarch.rpm", c)
        self.assertIn("--skip-unavailable rpmfusion-free-release-tainted rpmfusion-nonfree-release-tainted "
                      "rpmfusion-free-appstream-data rpmfusion-nonfree-appstream-data", c)
        self.assertTrue(os.path.exists(f"{d}/state/sources-done"))

    def test_release_packages_are_installed_before_their_extras(self):
        d, env = self.make()
        self.run_script(env)
        c = self.calls(d)
        self.assertLess(c.index("rpmfusion-nonfree-release-45.noarch.rpm"), c.index("appstream-data"))

    def test_everything_already_present_does_nothing_but_records_success(self):
        d, env = self.make(remotes="flathub\nflathub-beta\n", installed=[
            "rpmfusion-free-release", "rpmfusion-nonfree-release", "rpmfusion-free-release-tainted",
            "rpmfusion-nonfree-release-tainted", "rpmfusion-free-appstream-data", "rpmfusion-nonfree-appstream-data"])
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0)
        self.assertEqual(self.calls(d), "")
        self.assertTrue(os.path.exists(f"{d}/state/sources-done"))

    def test_dry_run_changes_nothing_and_records_nothing(self):
        d, env = self.make()
        rc, out = self.run_script(env, "--dry-run")
        self.assertEqual(rc, 0)
        self.assertEqual(self.calls(d), "")
        self.assertIn("DRY|flatpak remote-add", out)
        self.assertFalse(os.path.exists(f"{d}/state/sources-done"))

    def test_offline_fails_retries_and_does_not_record_success(self):
        d, env = self.make(dnf_fails=True, flatpak_fails=True)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(f"{d}/state/sources-done"))
        self.assertEqual(self.calls(d).count("if-not-exists flathub https://dl.flathub.org"), 6)   # retried six times

    def test_extras_are_not_attempted_when_rpm_fusion_itself_failed(self):
        d, env = self.make(dnf_fails=True)
        self.run_script(env)
        self.assertNotIn("appstream-data", self.calls(d))

    def test_flathub_beta_is_added_at_lowest_priority_after_flathub(self):
        d, env = self.make()
        self.run_script(env)
        c = self.calls(d)
        self.assertIn("flatpak remote-add --system --if-not-exists --prio=0 flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo", c)
        self.assertLess(c.index("flathub https://dl.flathub.org"), c.index("flathub-beta"))

    def test_flathub_beta_failure_is_not_fatal_and_still_records_success(self):
        d, env = self.make(beta_fails=True)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)
        self.assertIn("Could not add Flathub Beta (optional)", out)
        self.assertTrue(os.path.exists(f"{d}/state/sources-done"))

    def test_flathub_beta_can_be_switched_off(self):
        for setting in ('FLATHUB_BETA="no"\n', "FLATHUB_BETA=no\n"):
            d, env = self.make(conf=setting)
            rc, out = self.run_script(env)
            self.assertEqual(rc, 0, out)
            self.assertNotIn("flathub-beta", self.calls(d), setting)
            self.assertIn("if-not-exists flathub https://dl.flathub.org", self.calls(d))

    NO_CHOICE = "Third-party repositories are disabled (no selection has been made)"

    def test_third_party_is_enabled_when_nobody_has_chosen(self):
        d, env = self.make(third_party=self.NO_CHOICE)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)
        self.assertIn("fedora-third-party enable", self.calls(d))

    def test_third_party_runs_after_our_own_flathub_so_ours_stays_unfiltered(self):
        d, env = self.make(third_party=self.NO_CHOICE)
        self.run_script(env)
        c = self.calls(d)
        self.assertLess(c.index("if-not-exists flathub https://dl.flathub.org"), c.index("fedora-third-party enable"))

    def test_third_party_already_enabled_is_left_alone(self):
        d, env = self.make(third_party="Third-party repositories are enabled.")
        self.run_script(env)
        self.assertNotIn("fedora-third-party enable", self.calls(d))

    def test_third_party_explicitly_disabled_by_the_user_is_respected(self):
        d, env = self.make(third_party="Third-party repositories are disabled.")
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("fedora-third-party enable", self.calls(d))

    def test_third_party_tool_missing_is_not_an_error(self):
        d, env = self.make(third_party=None)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)

    def test_third_party_failure_retries_next_boot(self):
        d, env = self.make(third_party=self.NO_CHOICE, third_party_fails=True)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(f"{d}/state/sources-done"))

    def test_missing_flatpak_is_skipped_not_fatal(self):
        d, env = self.make(have_flatpak=False)
        rc, out = self.run_script(env)
        self.assertEqual(rc, 0, out)
        self.assertIn("skipping Flathub", out)

    def test_services_are_enabled_and_cannot_block_the_login_screen(self):
        root = os.path.join(HERE, "..", "root")
        links = {
            "etc/systemd/system/multi-user.target.wants/normie-sources.service": "/usr/lib/systemd/system/normie-sources.service",
            "etc/systemd/user/timers.target.wants/normie-remind.timer": "/usr/lib/systemd/user/normie-remind.timer",
        }
        for rel, target in links.items():
            p = os.path.join(root, rel)
            self.assertTrue(os.path.islink(p), rel)
            self.assertEqual(os.readlink(p), target)
        with open(os.path.join(root, "usr/lib/systemd/system/normie-sources.service")) as fh:
            unit = fh.read()
        self.assertIn("Type=simple", unit)
        self.assertIn("ConditionPathExists=!/var/lib/normie/sources-done", unit)


class NoSnap(unittest.TestCase):
    """Snap was removed on purpose (docs/DECISIONS.md D-13). These keep it from creeping back in."""
    ROOT = os.path.join(HERE, "..")

    def test_snap_packages_are_not_in_any_package_list(self):
        for rel in ("components/normie/tools.xml", "components/normie/deps.xml",
                    "components/normie/deps-universal.xml", "dist/normie-deps.list"):
            with open(os.path.join(self.ROOT, rel)) as fh:
                text = fh.read().lower()
            self.assertNotIn("snapd", text, rel)
            self.assertNotIn("discover-snap", text, rel)

    def test_snap_is_not_enabled_by_the_overlay(self):
        root = os.path.join(self.ROOT, "root")
        self.assertFalse(os.path.lexists(os.path.join(root, "snap")))
        self.assertFalse(os.path.lexists(os.path.join(root, "etc/systemd/system/sockets.target.wants/snapd.socket")))


class Reminder(unittest.TestCase):
    SCRIPT = os.path.join(HERE, "..", "root", "usr", "libexec", "normie", "normie-remind")
    DAY = 86400
    T0 = 1_800_000_000

    def make(self, last_update_days_ago=None, conf="", notify_answer="", first_seen_days_ago=None, reminded_days_ago=None,
             remote_list=None, applied_hash=None, told_hash=None, offline=False):
        d = tempfile.mkdtemp(prefix="normie-rem-")
        atexit.register(shutil.rmtree, d, True)
        for sub in ("bin", "sys", "user"):
            os.makedirs(f"{d}/{sub}")
        w(f"{d}/calls", "")
        w(f"{d}/conf", conf)
        if last_update_days_ago is not None:
            w(f"{d}/sys/last-update", f"{self.T0 - last_update_days_ago * self.DAY}\n")
        if first_seen_days_ago is not None:
            w(f"{d}/user/first-seen", f"{self.T0 - first_seen_days_ago * self.DAY}\n")
        if reminded_days_ago is not None:
            w(f"{d}/user/last-reminded", f"{self.T0 - reminded_days_ago * self.DAY}\n")
        if remote_list is not None:
            w(f"{d}/deplist", remote_list)
        if applied_hash is not None:
            w(f"{d}/sys/deps-applied", applied_hash + "\n")
        if told_hash is not None:
            w(f"{d}/user/deps-notified", told_hash + "\n")
        w(f"{d}/bin/curl", """#!/bin/sh
[ -e "$FAKE/offline" ] && exit 6
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
[ -n "$out" ] && [ -e "$FAKE/deplist" ] && cp "$FAKE/deplist" "$out"
exit 0
""", 0o755)
        if offline:
            w(f"{d}/offline", "")
        w(f"{d}/bin/notify-send", f'#!/bin/sh\necho "notify $*" >> "$FAKE/calls"\necho "{notify_answer}"\n', 0o755)
        w(f"{d}/gui", '#!/bin/sh\necho "gui started" >> "$FAKE/calls"\n', 0o755)
        env = dict(os.environ, FAKE=d, NORMIE_TEST="1", NORMIE_CONF=f"{d}/conf", NORMIE_STATE=f"{d}/sys",
                   NORMIE_USER_STATE=f"{d}/user", NORMIE_GUI=f"{d}/gui", NORMIE_NOW=str(self.T0), NORMIE_LIB=LIB,
                   PATH=f"{d}/bin:" + os.environ["PATH"])
        return d, env

    def run_script(self, env):
        return subprocess.run(["bash", self.SCRIPT], env=env, capture_output=True, text=True)

    def calls(self, d):
        with open(f"{d}/calls") as fh:
            return fh.read()

    def test_recent_update_means_no_reminder(self):
        d, env = self.make(last_update_days_ago=3)
        self.run_script(env)
        self.assertEqual(self.calls(d), "")

    def test_old_update_shows_reminder_with_days_and_action(self):
        d, env = self.make(last_update_days_ago=20)
        self.run_script(env)
        c = self.calls(d)
        self.assertIn("notify", c)
        self.assertIn("20 days ago", c)
        self.assertIn("--action=update=Update now", c)

    def test_clicking_update_now_opens_the_window(self):
        d, env = self.make(last_update_days_ago=20, notify_answer="update")
        self.run_script(env)
        self.assertIn("gui started", self.calls(d))

    def test_dismissing_does_not_open_the_window(self):
        d, env = self.make(last_update_days_ago=20, notify_answer="")
        self.run_script(env)
        self.assertNotIn("gui started", self.calls(d))

    def test_at_most_once_every_three_days(self):
        d, env = self.make(last_update_days_ago=20, reminded_days_ago=1)
        self.run_script(env)
        self.assertEqual(self.calls(d), "")
        d2, env2 = self.make(last_update_days_ago=20, reminded_days_ago=4)
        self.run_script(env2)
        self.assertIn("notify", self.calls(d2))

    def test_never_updated_counts_from_first_sight_not_from_forever(self):
        d, env = self.make()                    # no stamp, no first-seen: starts the clock, no nagging
        self.run_script(env)
        self.assertEqual(self.calls(d), "")
        self.assertTrue(os.path.exists(f"{d}/user/first-seen"))
        d2, env2 = self.make(first_seen_days_ago=30)
        self.run_script(env2)
        self.assertIn("30 days ago", self.calls(d2))

    def test_remind_days_setting_is_respected(self):
        d, env = self.make(last_update_days_ago=5, conf='REMIND_DAYS=3\n')
        self.run_script(env)
        self.assertIn("notify", self.calls(d))
        d2, env2 = self.make(last_update_days_ago=20, conf='REMIND_DAYS="30"\n')
        self.run_script(env2)
        self.assertEqual(self.calls(d2), "")

    # ---- "compatibility fixes are available"
    URL_CONF = 'DEPS_LIST_URL="https://example.invalid/normie-deps.list"\n'

    def test_newer_list_triggers_a_fix_notification_even_if_recently_updated(self):
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF, remote_list="gcc\nnewlib-fix\n",
                           applied_hash=names_hash(["gcc"]))
        self.run_script(env)
        c = self.calls(d)
        self.assertIn("Compatibility fixes are available", c)
        self.assertIn("--action=update=Update now", c)

    def test_fix_notification_opens_the_window_when_clicked(self):
        d, env = self.make(conf=self.URL_CONF, remote_list="a\nb\n", applied_hash=names_hash(["a"]), notify_answer="update")
        self.run_script(env)
        self.assertIn("gui started", self.calls(d))

    def test_same_list_means_no_fix_notification(self):
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF, remote_list="gcc\nfoo\n",
                           applied_hash=names_hash(["foo", "gcc"]))
        self.run_script(env)
        self.assertEqual(self.calls(d), "")

    def test_each_new_list_version_is_announced_only_once(self):
        new = ["a", "b"]
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF, remote_list="a\nb\n",
                           applied_hash=names_hash(["a"]), told_hash=names_hash(new))
        self.run_script(env)
        self.assertEqual(self.calls(d), "")

    def test_no_fix_notification_before_a_list_was_ever_applied(self):
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF, remote_list="a\n")   # no applied hash
        self.run_script(env)
        self.assertEqual(self.calls(d), "")

    def test_no_url_configured_means_no_network_use(self):
        d, env = self.make(last_update_days_ago=1, conf="", remote_list="a\n", applied_hash=names_hash(["x"]))
        self.run_script(env)
        self.assertEqual(self.calls(d), "")

    def test_offline_is_silent(self):
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF, remote_list="a\n",
                           applied_hash=names_hash(["x"]), offline=True)
        r = self.run_script(env)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.calls(d), "")

    def test_malicious_list_cannot_trigger_anything_but_a_notification(self):
        d, env = self.make(last_update_days_ago=1, conf=self.URL_CONF,
                           remote_list="--installroot=/x\nrm -rf /\n$(reboot)\n", applied_hash=names_hash(["x"]))
        self.run_script(env)
        self.assertEqual(self.calls(d), "")      # nothing valid in it: ignored, not announced, not run

    def test_timer_is_not_active_in_the_live_session(self):
        unit = os.path.join(HERE, "..", "root", "usr", "lib", "systemd", "user", "normie-remind.service")
        with open(unit) as fh:
            self.assertIn("ConditionPathExists=!/run/initramfs/livedev", fh.read())


if __name__ == "__main__":
    unittest.main()
