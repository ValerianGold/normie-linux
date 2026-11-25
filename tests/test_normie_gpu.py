#!/usr/bin/env python3
"""
Tests for packaging/normie-tools/files/usr/libexec/normie/normie-gpu using a fake PCI bus and fake commands.
Nothing here touches the real system.   Run:  python3 -m unittest discover -s tests -v
"""
import atexit
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GPU = os.path.join(HERE, "..", "packaging", "normie-tools", "files", "usr", "libexec", "normie", "normie-gpu")

STUBS = {
    "lspci": '#!/bin/sh\n# usage: lspci -s SLOT -mm\ngrep "^$2|" "$FAKE/lspci" | cut -d"|" -f2-\n',
    "rpm": '''#!/bin/sh
if [ "$2" = "kernel-core" ]; then cat "$FAKE/kernels" 2>/dev/null; exit 0; fi
grep -qx "$2" "$FAKE/installed" 2>/dev/null && { echo "$2-1.0"; exit 0; }
echo "package $2 is not installed"; exit 1
''',
    "modinfo": '#!/bin/sh\n# modinfo -k KVER -F version nvidia\ngrep -qx "$2" "$FAKE/modules" 2>/dev/null && { echo 595.58.03; exit 0; }\nexit 1\n',
    "mokutil": '''#!/bin/sh
case "$1" in
  --sb-state) cat "$FAKE/sb" ;;
  --test-key) grep -q enrolled "$FAKE/mok" 2>/dev/null && { echo "already enrolled"; exit 0; }; exit 1 ;;
  --list-new) grep -q pending "$FAKE/mok" 2>/dev/null && echo "SHA1 Fingerprint: aa:bb"; exit 0 ;;
  --generate-hash=*) echo '$6$fakehash' ;;
  *) echo "mokutil $*" >> "$FAKE/calls" ;;
esac
''',
}
for name in ("dnf", "akmods", "kmodgenca", "grubby"):
    STUBS[name] = f'#!/bin/sh\necho "{name} $*" >> "$FAKE/calls"\n'


def w(path, text):
    with open(path, "w") as fh:
        fh.write(text)


class Env:
    def __init__(self, gpus, installed=(), kernels=("6.20.1-100.fc45.x86_64",), modules=(),
                 sb="SecureBoot disabled", mok="", nonfree=True):
        d = tempfile.mkdtemp(prefix="normie-test-")
        atexit.register(shutil.rmtree, d, True)
        self.fake = d
        os.makedirs(f"{d}/bin")
        os.makedirs(f"{d}/sys/bus/pci/devices")
        lspci = []
        for i, (dev, name) in enumerate(gpus):
            slot = f"0000:0{i+1}:00.0"
            p = f"{d}/sys/bus/pci/devices/{slot}"
            os.makedirs(p)
            w(f"{p}/vendor", "0x10de\n")
            w(f"{p}/class", "0x030000\n")
            w(f"{p}/device", f"0x{dev:04x}\n")
            if name:
                lspci.append(f'{slot}|"0{i+1}:00.0" "VGA compatible controller" "NVIDIA Corporation" "{name}" -r a1')
        # an Intel iGPU that must be ignored
        p = f"{d}/sys/bus/pci/devices/0000:00:02.0"
        os.makedirs(p)
        w(f"{p}/vendor", "0x8086\n")
        w(f"{p}/class", "0x030000\n")
        w(f"{p}/device", "0x9a49\n")
        inst = list(installed) + (["rpmfusion-nonfree-release"] if nonfree else [])
        w(f"{d}/lspci", "\n".join(lspci) + "\n")
        w(f"{d}/installed", "\n".join(inst) + "\n")
        w(f"{d}/kernels", "\n".join(kernels) + "\n")
        w(f"{d}/modules", "\n".join(modules) + "\n")
        w(f"{d}/sb", sb + "\n")
        w(f"{d}/mok", mok)
        w(f"{d}/calls", "")
        for n, body in STUBS.items():
            path = f"{d}/bin/{n}"
            w(path, body)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        self.env = dict(os.environ, FAKE=d, NORMIE_SYSFS=f"{d}/sys",
                        PATH=f"{d}/bin:" + os.environ["PATH"],
                        NORMIE_RUNNING_KERNEL=kernels[-1])

    def run(self, *args):
        r = subprocess.run([sys.executable, GPU, *args], env=self.env, capture_output=True, text=True)
        return r.returncode, r.stdout

    def calls(self):
        with open(f"{self.fake}/calls") as fh:
            return fh.read()


class Detection(unittest.TestCase):
    def check(self, dev, name, branch):
        e = Env([(dev, name)])
        rc, out = e.run("detect")
        self.assertIn(f"Chosen driver branch: {branch}", out, out)

    def test_pascal_gtx1060_uses_580xx(self):   self.check(0x1C03, "GP106 [GeForce GTX 1060 6GB]", "580xx")
    def test_maxwell_gtx970_uses_580xx(self):   self.check(0x13C2, "GM204 [GeForce GTX 970]", "580xx")
    def test_volta_uses_580xx(self):            self.check(0x1D81, "GV100 [TITAN V]", "580xx")
    def test_turing_rtx2060_current(self):      self.check(0x1F08, "TU106 [GeForce RTX 2060]", "current")
    def test_ampere_current(self):              self.check(0x2504, "GA106 [GeForce RTX 3060]", "current")
    def test_ada_current(self):                 self.check(0x2786, "AD104 [GeForce RTX 4070]", "current")
    def test_blackwell_current(self):           self.check(0x2B85, "GB202 [GeForce RTX 5090]", "current")
    def test_kepler_stays_on_nouveau(self):     self.check(0x1180, "GK104 [GeForce GTX 680]", "none")
    def test_fermi_stays_on_nouveau(self):      self.check(0x06C0, "GF100 [GeForce GTX 480]", "none")
    def test_ancient_stays_on_nouveau(self):    self.check(0x0A20, "GT216 [GeForce GT 220]", "none")
    def test_unknown_old_id_does_nothing(self): self.check(0x1234, None, "none")
    def test_unnamed_new_id_assumed_current(self):
        # pci.ids on the machine is older than the card: name missing, id >= 0x1E00
        self.check(0x2F00, None, "current")

    def test_no_nvidia_at_all(self):
        rc, out = Env([]).run("plan")
        self.assertEqual(rc, 0)
        self.assertIn("No NVIDIA graphics card found", out)

    def test_two_different_branches_leaves_system_alone(self):
        e = Env([(0x1C03, "GP106 [GeForce GTX 1060 6GB]"), (0x2504, "GA106 [GeForce RTX 3060]")])
        rc, out = e.run("plan")
        self.assertEqual(rc, 0)
        self.assertIn("different drivers", out)


class Planning(unittest.TestCase):
    GPU_NEW = [(0x2504, "GA106 [GeForce RTX 3060]")]
    GPU_OLD = [(0x1C03, "GP106 [GeForce GTX 1060 6GB]")]

    def test_fresh_system_needs_install(self):
        rc, out = Env(self.GPU_NEW).run("plan")
        self.assertEqual(rc, 10)
        self.assertIn("Action needed: install", out)

    def test_up_to_date_needs_nothing(self):
        e = Env(self.GPU_NEW, installed=["akmod-nvidia"], modules=["6.20.1-100.fc45.x86_64"])
        self.assertEqual(e.run("plan")[0], 0)

    def test_installed_but_not_built_needs_build(self):
        rc, out = Env(self.GPU_NEW, installed=["akmod-nvidia"]).run("plan")
        self.assertEqual(rc, 10)
        self.assertIn("build", out)

    def test_wrong_branch_after_fedora_upgrade_is_swapped(self):
        # a GTX 1060 that ended up with the 'current' driver
        rc, out = Env(self.GPU_OLD, installed=["akmod-nvidia"]).run("plan")
        self.assertEqual(rc, 10)
        self.assertIn("swap", out)

    def test_secure_boot_key_not_enrolled(self):
        e = Env(self.GPU_NEW, installed=["akmod-nvidia"], modules=["6.20.1-100.fc45.x86_64"],
                sb="SecureBoot enabled", mok="")
        w(f"{e.fake}/key.der", "x")
        e.env["NORMIE_AKMODS_KEY"] = f"{e.fake}/key.der"
        rc, out = e.run("plan")
        self.assertEqual(rc, 10)
        self.assertIn("Action needed: enroll", out)

    def test_secure_boot_key_already_enrolled_needs_nothing(self):
        e = Env(self.GPU_NEW, installed=["akmod-nvidia"], modules=["6.20.1-100.fc45.x86_64"],
                sb="SecureBoot enabled", mok="enrolled")
        w(f"{e.fake}/key.der", "x")
        e.env["NORMIE_AKMODS_KEY"] = f"{e.fake}/key.der"
        self.assertEqual(e.run("plan")[0], 0)

    def test_quiet_hides_info(self):
        rc, out = Env(self.GPU_NEW).run("plan", "--quiet")
        self.assertEqual(rc, 10)
        self.assertNotIn("INFO|", out)


class Apply(unittest.TestCase):
    def test_install_modern_card_dry_run_commands(self):
        rc, out = Env([(0x2504, "GA106 [GeForce RTX 3060]")]).run("apply", "--dry-run")
        self.assertEqual(rc, 0, out)
        self.assertIn("DRY|dnf install -y akmod-nvidia xorg-x11-drv-nvidia xorg-x11-drv-nvidia-libs.i686 "
                      "xorg-x11-drv-nvidia-cuda libva-nvidia-driver libva-nvidia-driver.i686", out)
        self.assertNotIn("--allowerasing", out)
        self.assertIn("DRY|akmods --force --kernels 6.20.1-100.fc45.x86_64", out)
        self.assertIn("NEEDS_REBOOT|", out)

    def test_pascal_gets_580xx_packages(self):
        rc, out = Env([(0x1C03, "GP106 [GeForce GTX 1060 6GB]")]).run("apply", "--dry-run")
        self.assertIn("akmod-nvidia-580xx", out)
        self.assertIn("xorg-x11-drv-nvidia-580xx-libs.i686", out)
        self.assertNotIn(" akmod-nvidia ", out)

    def test_swap_uses_allowerasing(self):
        rc, out = Env([(0x1C03, "GP106 [GeForce GTX 1060 6GB]")], installed=["akmod-nvidia"]).run("apply", "--dry-run")
        self.assertIn("--allowerasing", out)

    def test_dry_run_changes_nothing(self):
        e = Env([(0x2504, "GA106 [GeForce RTX 3060]")])
        e.run("apply", "--dry-run")
        self.assertEqual(e.calls(), "", "dry-run must not execute any command")

    def test_old_card_apply_does_nothing(self):
        e = Env([(0x1180, "GK104 [GeForce GTX 680]")])
        rc, out = e.run("apply", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertNotIn("dnf install", out)

    def test_missing_repo_blocks_real_install_safely(self):
        e = Env([(0x2504, "GA106 [GeForce RTX 3060]")], nonfree=False)
        e.env["NORMIE_SYSFS"] = f"{e.fake}/sys"
        rc, out = e.run("apply")          # not dry-run, not root in the test -> must refuse
        self.assertEqual(rc, 1)
        self.assertEqual(e.calls(), "")

    def test_secure_boot_dry_run_shows_password_and_reboot(self):
        e = Env([(0x2504, "GA106 [GeForce RTX 3060]")], sb="SecureBoot enabled")
        rc, out = e.run("apply", "--dry-run")
        self.assertRegex(out, r"MOK\|\d{8}")
        self.assertIn("kmodgenca -a", out)
        # key must be created before modules are built
        self.assertLess(out.index("kmodgenca"), out.index("akmods --force"))


if __name__ == "__main__":
    unittest.main()
