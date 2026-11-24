"""
Tests for tools/build.sh and tools/write-build-info.sh using a FAKE kiwi-build (no real image is built).
The fake refuses to build into a folder that already holds an ISO, like real kiwi does, so these tests
prove the script clears and archives correctly. They need root (build.sh re-runs itself through sudo
otherwise), so they are skipped for ordinary users.   Run:  sudo python3 -m unittest discover -s tests -v
"""
import atexit
import glob
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

FAKE_KIWI = r'''#!/bin/bash
# fake kiwi-build: parses the arguments build.sh passes and "builds" an ISO
for a in "$@"; do case "$a" in --output-dir=*) out="${a#*=}" ;; --image-profile=*) prof="${a#*=}" ;; esac; done
[ -n "${FAKE_KIWI_RC:-}" ] && [ "$FAKE_KIWI_RC" != 0 ] && { echo "fake kiwi: simulated failure"; exit "$FAKE_KIWI_RC"; }
if ls "$out-build"/*.iso >/dev/null 2>&1; then echo "fake kiwi: Root directory already exists"; exit 3; fi
mkdir -p "$out-build"
printf '%s' "${FAKE_ISO_CONTENT:-iso}" > "$out-build/Normie-Linux.x86_64-45.iso"
echo "fake kiwi: built $prof"
'''


def read(path):
    with open(path) as fh:
        return fh.read()


def sh(*cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


@unittest.skipIf(os.geteuid() != 0, "needs root (the build script re-runs itself through sudo otherwise)")
class BuildScript(unittest.TestCase):
    def make_repo(self):
        d = tempfile.mkdtemp(prefix="normie-build-")
        atexit.register(shutil.rmtree, d, True)
        os.makedirs(f"{d}/tools")
        for name in ("build.sh", "write-build-info.sh"):
            shutil.copy(os.path.join(ROOT, "tools", name), f"{d}/tools/{name}")
        with open(f"{d}/kiwi-build", "w") as fh:
            fh.write(FAKE_KIWI)
        os.chmod(f"{d}/kiwi-build", 0o755)
        with open(f"{d}/.gitignore", "w") as fh:
            fh.write("root/usr/share/normie/build-info\n")
        with open(f"{d}/file.txt", "w") as fh:
            fh.write("one\n")
        sh("git", "init", "-q", "-b", "main", cwd=d)
        self.commit(d, "first")
        return d

    def commit(self, d, msg):
        with open(f"{d}/file.txt", "a") as fh:
            fh.write(msg + "\n")
        sh("git", "add", "-A", cwd=d)
        sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg, cwd=d)
        return sh("git", "rev-parse", "--short=12", "HEAD", cwd=d).stdout.strip()

    def build(self, d, out, content="iso", rc="0", profile="Normie-Full-Live"):
        env = dict(os.environ, NORMIE_OUT=out, NORMIE_USER="root", FAKE_ISO_CONTENT=content, FAKE_KIWI_RC=rc)
        env.pop("SUDO_USER", None)
        return sh("bash", f"{d}/tools/build.sh", profile, cwd=d, env=env)

    def out_dir(self):
        o = tempfile.mkdtemp(prefix="normie-out-")
        atexit.register(shutil.rmtree, o, True)
        return o

    def test_first_build_records_version_and_keeps_a_named_copy(self):
        d, out = self.make_repo(), self.out_dir()
        commit = sh("git", "rev-parse", "--short=12", "HEAD", cwd=d).stdout.strip()
        r = self.build(d, out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        iso = f"{out}/Normie-Full-Live-build/Normie-Linux.x86_64-45.iso"
        self.assertTrue(os.path.exists(iso))
        with open(f"{out}/Normie-Full-Live-build/BUILD-INFO.txt") as fh:
            info = fh.read()
        self.assertIn(f"NORMIE_BUILD_COMMIT={commit}", info)
        self.assertIn("NORMIE_BUILD_PROFILE=Normie-Full-Live", info)
        self.assertIn("NORMIE_BUILD_UNCOMMITTED_CHANGES=no", info)
        named = f"{out}/isos/Normie-Linux.x86_64-45-Normie-Full-Live-{commit}.iso"
        self.assertTrue(os.path.exists(named))
        self.assertEqual(os.stat(named).st_ino, os.stat(iso).st_ino)      # a hard link: no extra disk space
        self.assertIn(f"Built from commit {commit}", r.stdout)
        # the same information goes INTO the image
        with open(f"{d}/root/usr/share/normie/build-info") as fh:
            self.assertIn(f"NORMIE_BUILD_COMMIT={commit}", fh.read())

    def test_rebuilding_into_the_same_folder_works_and_keeps_the_old_iso(self):
        d, out = self.make_repo(), self.out_dir()
        c1 = sh("git", "rev-parse", "--short=12", "HEAD", cwd=d).stdout.strip()
        self.assertEqual(self.build(d, out, content="OLD-ISO").returncode, 0)
        c2 = self.commit(d, "second")
        r = self.build(d, out, content="NEW-ISO")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)      # the fake refuses an existing ISO, so this proves clearing
        self.assertEqual(read(f"{out}/Normie-Full-Live-build/Normie-Linux.x86_64-45.iso"), "NEW-ISO")
        with open(f"{out}/Normie-Full-Live-build/BUILD-INFO.txt") as fh:
            self.assertIn(f"NORMIE_BUILD_COMMIT={c2}", fh.read())
        kept = {os.path.basename(p): read(p) for p in glob.glob(f"{out}/isos/*.iso")}
        self.assertEqual(sorted(kept.values()), ["NEW-ISO", "OLD-ISO"])      # each ISO kept once, named by its commit
        self.assertTrue(any(n.endswith(f"-{c1}.iso") for n in kept))
        self.assertTrue(any(n.endswith(f"-{c2}.iso") for n in kept))
        self.assertIn("already kept", r.stdout)

    def test_an_iso_from_before_version_tracking_is_kept_too(self):
        # the real situation: an ISO already sits in the folder from an older build
        d, out = self.make_repo(), self.out_dir()
        os.makedirs(f"{out}/Normie-Full-Live-build")
        with open(f"{out}/Normie-Full-Live-build/Normie-Linux.x86_64-45.iso", "w") as fh:
            fh.write("ANCIENT")
        r = self.build(d, out, content="FRESH")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(read(f"{out}/Normie-Full-Live-build/Normie-Linux.x86_64-45.iso"), "FRESH")
        kept = {os.path.basename(p): read(p) for p in glob.glob(f"{out}/isos/*.iso")}
        self.assertEqual(sorted(kept.values()), ["ANCIENT", "FRESH"])
        self.assertTrue(any("-earlier-" in n and v == "ANCIENT" for n, v in kept.items()))
        self.assertIn("Kept the previous ISO", r.stdout)

    def test_a_failed_build_says_so_and_still_keeps_the_previous_iso(self):
        d, out = self.make_repo(), self.out_dir()
        self.build(d, out, content="GOOD")
        r = self.build(d, out, content="BAD", rc="1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("BUILD FAILED", r.stdout)
        self.assertIn("GOOD", [read(p) for p in glob.glob(f"{out}/isos/*.iso")])

    def test_uncommitted_changes_are_flagged_in_the_info_and_the_name(self):
        d, out = self.make_repo(), self.out_dir()
        with open(f"{d}/file.txt", "a") as fh:
            fh.write("not committed\n")
        r = self.build(d, out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(f"{out}/Normie-Full-Live-build/BUILD-INFO.txt") as fh:
            self.assertIn("NORMIE_BUILD_UNCOMMITTED_CHANGES=yes", fh.read())
        self.assertTrue(glob.glob(f"{out}/isos/*-uncommitted.iso"))

    def test_separate_profiles_do_not_disturb_each_other(self):
        d, out = self.make_repo(), self.out_dir()
        self.assertEqual(self.build(d, out, content="LIVE", profile="Normie-Live").returncode, 0)
        self.assertEqual(self.build(d, out, content="FULL", profile="Normie-Full-Live").returncode, 0)
        self.assertEqual(read(f"{out}/Normie-Live-build/Normie-Linux.x86_64-45.iso"), "LIVE")

    def test_the_generated_file_is_never_committed(self):
        with open(os.path.join(ROOT, ".gitignore")) as fh:
            self.assertIn("root/usr/share/normie/build-info", fh.read())

    def test_unknown_profile_is_refused_before_anything_happens(self):
        d, out = self.make_repo(), self.out_dir()
        r = self.build(d, out, profile="Nonsense")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(f"{out}/isos"))


if __name__ == "__main__":
    unittest.main()
