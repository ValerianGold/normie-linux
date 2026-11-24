"""Tests for the rebrand: the image description names our packages and no Fedora-branded ones, the
package build script, the extra package checks, and the branding audit."""
import atexit
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as fh:
        return fh.read()


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def tmpdir():
    d = tempfile.mkdtemp(prefix="normie-rebrand-")
    atexit.register(shutil.rmtree, d, True)
    return d


def packages_for(profile):
    """(named, ignored, bootstrap) package names active for a Normie profile, read the way KIWI would."""
    kiwi = ET.parse(os.path.join(ROOT, "Normie-Linux.kiwi")).getroot()
    files = ["Normie-Linux.kiwi"] + [i.get("from").replace("this://./", "") for i in kiwi.findall("include")]
    requires = {}
    roots = []
    for f in files:
        r = ET.parse(os.path.join(ROOT, f)).getroot()
        roots.append(r)
        for p in r.iter("profile"):
            requires.setdefault(p.get("name"), []).extend(q.get("profile") for q in p.findall("requires"))
    active, todo = set(), [profile]
    while todo:
        p = todo.pop()
        if p not in active:
            active.add(p)
            todo.extend(requires.get(p, []))
    named, ignored, boot = set(), set(), set()
    for r in roots:
        for grp in r.iter("packages"):
            profs = grp.get("profiles")
            if profs is not None and not (active & {x.strip() for x in profs.split(",")}):
                continue
            for c in grp:
                if c.tag == "package":
                    named.add(c.get("name"))
                    if grp.get("type") == "bootstrap":
                        boot.add(c.get("name"))
                elif c.tag == "ignore":
                    ignored.add(c.get("name"))
    return named, ignored, boot, active


class ImageDescription(unittest.TestCase):
    def test_normie_profiles_no_longer_build_on_fedoras_kde_live_profile(self):
        for profile in ("Normie-Live", "Normie-Full-Live"):
            _, _, _, active = packages_for(profile)
            self.assertNotIn("KDE-Desktop-Live", active, profile)
            self.assertIn("KDE-Desktop", active)
            self.assertIn("LiveInstall", active)

    def test_the_images_install_our_packages_in_the_right_stage(self):
        for profile in ("Normie-Live", "Normie-Full-Live"):
            named, _, boot, _ = packages_for(profile)
            self.assertIn("normie-release", boot, profile)
            for n in ("normie-logos", "normie-backgrounds-kde", "normie-lookandfeel"):
                self.assertIn(n, named, profile)

    def test_no_fedora_branded_package_is_installed(self):
        banned = re.compile(r"^(fedora-release.*|fedora-logos.*|generic-(release|logos).*|f\d+-backgrounds.*|"
                            r"desktop-backgrounds-kde|plasma-welcome-fedora|"
                            r"breeze-icon-theme-fedora|fedora-bookmarks)$")
        for profile in ("Normie-Live", "Normie-Full-Live"):
            named, _, _, _ = packages_for(profile)
            self.assertEqual([n for n in named if banned.match(n)], [], profile)

    def test_fedoras_branded_packages_are_excluded_so_nothing_pulls_them_back_in(self):
        _, ignored, _, _ = packages_for("Normie-Live")
        for n in ("fedora-release-kde", "fedora-release-common", "fedora-release-identity-kde-desktop", "fedora-logos",
                  "f45-backgrounds-base", "f45-backgrounds-kde", "desktop-backgrounds-kde",
                  "plasma-welcome-fedora", "breeze-icon-theme-fedora", "fedora-bookmarks"):
            self.assertIn(n, ignored)

    def test_the_two_packages_fedora_itself_requires_are_not_excluded(self):
        # plasma-workspace needs plasma-lookandfeel-fedora at its exact version, and abrt-desktop needs
        # libreport-fedora; excluding them makes the whole image unresolvable (found by solve-check)
        _, ignored, _, _ = packages_for("Normie-Live")
        self.assertNotIn("plasma-lookandfeel-fedora", ignored)
        self.assertNotIn("libreport-fedora", ignored)

    def test_fedoras_repositories_and_tools_are_never_excluded(self):
        _, ignored, _, _ = packages_for("Normie-Full-Live")
        for n in ("fedora-repos", "fedora-gpg-keys", "fedora-third-party", "fedora-flathub-remote",
                  "fedora-workstation-repositories", "fedora-appstream-metadata", "NetworkManager-config-connectivity-fedora",
                  "plasma-welcome", "normie-release", "normie-logos"):
            self.assertNotIn(n, ignored)

    def test_what_plasma_welcome_fedora_used_to_bring_in_is_still_installed(self):
        named, _, _, _ = packages_for("Normie-Live")
        for n in ("plasma-welcome", "fedora-flathub-remote", "fedora-third-party", "fedora-workstation-repositories"):
            self.assertIn(n, named)

    def test_every_normie_package_named_in_the_image_has_a_spec(self):
        have = {os.path.basename(p) for p in os.listdir(os.path.join(ROOT, "packaging"))
                if os.path.isdir(os.path.join(ROOT, "packaging", p))}
        named, _, _, _ = packages_for("Normie-Full-Live")
        for n in named:
            if n.startswith("normie-"):
                self.assertIn(n, have)

    def test_the_local_repository_is_build_time_only_and_unsigned_only_for_itself(self):
        root = ET.parse(os.path.join(ROOT, "repositories", "normie-local.xml")).getroot()
        repos = root.findall("repository")
        self.assertEqual(len(repos), 1)
        r = repos[0]
        self.assertEqual(r.get("alias"), "normie-local")
        self.assertEqual(r.get("imageinclude"), "false")                    # never reaches an installed system
        self.assertEqual(r.get("package_gpgcheck"), "false")
        self.assertEqual(r.find("source").get("path"), "dir:///var/lib/normie-linux/rpms")
        # Fedora's and RPM Fusion's repositories keep full checking
        for name in ("core.xml", "rpmfusion.xml"):
            self.assertNotIn("gpgcheck=\"false\"", read("repositories", name))

    def test_the_kiwi_file_includes_the_new_files(self):
        text = read("Normie-Linux.kiwi")
        self.assertIn("repositories/normie-local.xml", text)
        self.assertIn("components/normie/branding.xml", text)

    def test_the_iso_publisher_is_no_longer_fedora(self):
        text = read("components", "liveinstall.xml")
        self.assertNotIn('publisher="Fedora', text)
        self.assertEqual(text.count('publisher="Normie Linux contributors"'), 4)

    def test_the_boot_menu_entries_no_longer_use_the_fedora_class(self):
        self.assertNotIn("--class fedora", read("grub-x86.cfg.iso-template"))

    def test_fedoras_own_kde_team_file_is_left_untouched_for_upstream_merging(self):
        text = read("teams", "kde.xml")
        self.assertIn("fedora-release-kde", text)                           # still Fedora's file, as shipped
        self.assertIn("plasma-welcome-fedora", text)

    def test_validate_kiwi_passes_and_reports_the_branding_check(self):
        r = subprocess.run([sys.executable, "tools/validate-kiwi.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Branding: Normie-Full-Live installs our release", r.stdout)

    def test_validate_kiwi_catches_a_fedora_branded_package(self):
        d = tmpdir()
        shutil.copytree(ROOT, d + "/r", symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        path = d + "/r/components/normie/tools.xml"
        write(path, read("components", "normie", "tools.xml").replace(
            '<package name="curl"/>', '<package name="curl"/><package name="fedora-logos"/>'))
        r = subprocess.run([sys.executable, "tools/validate-kiwi.py"], cwd=d + "/r", capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("fedora-logos", r.stdout)

    def test_check_packages_counts_our_own_packages_as_available(self):
        # run it as a program with an empty list of online packages: only our four may be found
        d = tmpdir()
        avail = d + "/avail.txt"
        write(avail, "filesystem.x86_64\n")
        probe = d + "/probe.xml"
        write(probe, '<image><packages type="image"><package name="normie-release"/><package name="normie-logos"/>'
                     '<package name="normie-lookandfeel"/><package name="normie-backgrounds-kde"/>'
                     '<package name="not-a-package"/></packages></image>')
        r = subprocess.run([sys.executable, "tools/check-packages.py", "--avail-file", avail, probe], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertIn("not-a-package", r.stdout)
        self.assertNotIn("normie-release", r.stdout.split("NOT FOUND")[1])
        self.assertNotIn("normie-logos", r.stdout.split("NOT FOUND")[1])

    def test_solve_check_adds_the_local_repository_and_the_exclusions(self):
        r = subprocess.run([sys.executable, "tools/solve-check.py", "--print-only", "Normie-Full-Live"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--repofrompath=normie-local,file:///var/lib/normie-linux/rpms", r.stdout)
        self.assertRegex(r.stdout, r"\d+ excluded")
        self.assertNotIn(" 0 excluded", r.stdout)

    def test_the_baseline_fedora_profile_does_not_use_the_local_repository(self):
        r = subprocess.run([sys.executable, "tools/solve-check.py", "--print-only", "KDE-Desktop-Live"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertNotIn("normie-local", r.stdout)


class ConfigScript(unittest.TestCase):
    def test_the_default_look_and_feel_substitution_handles_all_three_fedora_packs(self):
        text = read("config.sh")
        m = re.search(r'sed -i -E "(s/[^"]+)"', text)
        self.assertTrue(m)
        expr = m.group(1).replace("$NORMIE_LNF", "org.normielinux.normie.desktop")
        d = tmpdir()
        for pack in ("fedora", "fedoradark", "fedoralight"):
            f = f"{d}/{pack}"
            write(f, f"[KDE]\nLookAndFeelPackage=org.fedoraproject.{pack}.desktop\n")
            subprocess.run(["sed", "-i", "-E", expr, f], check=True)
            self.assertEqual(read(f), "[KDE]\nLookAndFeelPackage=org.normielinux.normie.desktop\n")

    def test_it_only_runs_for_normie_profiles_and_the_script_is_valid_bash(self):
        r = subprocess.run(["bash", "-n", os.path.join(ROOT, "config.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        block = read("config.sh").split("NORMIE-LINUX CHANGE: default Plasma look and feel")[1].split("Set SELinux booleans")[0]
        self.assertIn('if [[ "$kiwi_profiles" == *"Normie"* ]]', block)


class InstallerProfileBlock(unittest.TestCase):
    """The 'installer profile' block of config.sh, run on a scratch folder."""

    def run_block(self, pdir, profiles="Normie-Full-Live"):
        block = read("config.sh").split("NORMIE-LINUX CHANGE: installer profile")[1].split("Set SELinux booleans")[0]
        block = block.split("\n", 1)[1]                      # drop the rest of the comment header line
        script = "kiwi_profiles=%s\n%s" % (profiles, "\n".join(l for l in block.splitlines() if not l.startswith("#")))
        r = subprocess.run(["bash", "-c", script], env=dict(os.environ, NORMIE_PROFILE_DIR=pdir), capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_it_makes_a_normie_copy_of_the_kde_profile(self):
        d = tmpdir()
        write(d + "/fedora-kde.conf", FEDORA_KDE_PROFILE)
        rc, out = self.run_block(d)
        self.assertEqual(rc, 0, out)
        self.assertEqual(read_file(d + "/normie-kde.conf"), NORMIE_PROFILE)
        self.assertEqual(read_file(d + "/fedora-kde.conf"), FEDORA_KDE_PROFILE)     # Fedora's own is untouched

    def test_it_makes_nothing_for_a_profile_it_does_not_understand(self):
        d = tmpdir()
        write(d + "/fedora-kde.conf", "[Profile]\nname: odd\n")
        rc, out = self.run_block(d)
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING", out)
        self.assertFalse(os.path.exists(d + "/normie-kde.conf"))

    def test_it_warns_when_fedoras_profile_is_missing_and_skips_non_normie_profiles(self):
        d = tmpdir()
        rc, out = self.run_block(d)
        self.assertIn("WARNING", out)
        write(d + "/fedora-kde.conf", FEDORA_KDE_PROFILE)
        rc, out = self.run_block(d, profiles="Container")
        self.assertFalse(os.path.exists(d + "/normie-kde.conf"))


class BuildRpmsScript(unittest.TestCase):
    """tools/build-rpms.sh with fake rpmbuild and createrepo_c."""
    FAKE_RPMBUILD = r'''#!/bin/bash
# fake rpmbuild: records its arguments, writes an "rpm" named after the spec
for a in "$@"; do case "$a" in *.spec) spec="$a" ;; esac; done
echo "$*" >> "$FAKE_LOG"
[ -n "${FAKE_RPMBUILD_FAIL:-}" ] && { echo "error: bad spec"; exit 1; }
top=""; prev=""
for a in "$@"; do [ "$prev" = "--define" ] && case "$a" in _topdir\ *) top="${a#_topdir }" ;; esac; prev="$a"; done
mkdir -p "$top/RPMS/noarch"
n="$(sed -n 's/^Name:[[:space:]]*//p' "$spec" | head -n1)"
echo rpm > "$top/RPMS/noarch/$n-1-1.noarch.rpm"
'''
    FAKE_CREATEREPO = r'''#!/bin/bash
echo "createrepo_c $*" >> "$FAKE_LOG"
for a in "$@"; do last="$a"; done
mkdir -p "$last/repodata"; echo meta > "$last/repodata/repomd.xml"
'''

    def setUp(self):
        d = tmpdir()
        self.d = d
        self.repo = d + "/repo"
        self.bin = d + "/bin"
        self.log = d + "/calls.log"
        self.local = d + "/local-repo"
        shutil.copytree(os.path.join(ROOT, "packaging"), self.repo + "/packaging")
        os.makedirs(self.repo + "/tools")
        shutil.copy(os.path.join(ROOT, "tools", "build-rpms.sh"), self.repo + "/tools/build-rpms.sh")
        write(self.repo + "/Normie-Linux.kiwi", "<image><description><contact>TODO</contact></description></image>")
        write(self.bin + "/rpmbuild", self.FAKE_RPMBUILD, 0o755)
        write(self.bin + "/createrepo_c", self.FAKE_CREATEREPO, 0o755)
        write(self.log, "")
        self.env = dict(os.environ, PATH=self.bin + ":" + os.environ["PATH"], NORMIE_TEST="1",
                        NORMIE_LOCAL_REPO=self.local, FAKE_LOG=self.log)
        self.env.pop("FAKE_RPMBUILD_FAIL", None)

    def run_script(self, *args, **extra):
        env = dict(self.env, **extra)
        r = subprocess.run(["bash", self.repo + "/tools/build-rpms.sh", *args], cwd="/", env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def calls(self):
        return [l for l in read_file(self.log).splitlines() if l]

    def test_it_builds_each_package_and_publishes_one_repository(self):
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        rpms = sorted(f for f in os.listdir(self.local) if f.endswith(".rpm"))
        self.assertEqual(len(rpms), 4, rpms)
        self.assertTrue(os.path.exists(self.local + "/repodata/repomd.xml"))
        self.assertEqual(len([c for c in self.calls() if c.startswith("-bb")]), 4)
        self.assertEqual(len([c for c in self.calls() if c.startswith("createrepo_c")]), 1)

    def test_the_sources_folder_is_the_packages_own_folder(self):
        self.run_script()
        for c in self.calls():
            if c.startswith("-bb"):
                spec = [w for w in c.split() if w.endswith(".spec")][0]
                self.assertIn("_sourcedir " + self.repo + "/" + os.path.dirname(spec), c)

    def test_the_project_address_from_the_kiwi_file_goes_into_the_packages(self):
        write(self.repo + "/Normie-Linux.kiwi",
              "<image><description><contact>https://github.com/someone/normie-linux</contact></description></image>")
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        self.assertIn("normie_home_url https://github.com/someone/normie-linux", " ".join(self.calls()))

    def test_an_unset_project_address_is_mentioned_and_not_passed(self):
        rc, out = self.run_script()
        self.assertIn("project address is not set", out)
        self.assertNotIn("normie_home_url", " ".join(self.calls()))

    def test_if_needed_skips_when_nothing_changed(self):
        self.run_script()
        open(self.log, "w").close()
        rc, out = self.run_script("--if-needed")
        self.assertEqual(rc, 0, out)
        self.assertIn("up to date", out)
        self.assertEqual(self.calls(), [])

    def test_if_needed_rebuilds_after_a_change_in_packaging(self):
        self.run_script()
        with open(self.repo + "/packaging/normie-release/issue", "a") as fh:
            fh.write("changed\n")
        open(self.log, "w").close()
        rc, out = self.run_script("--if-needed")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len([c for c in self.calls() if c.startswith("-bb")]), 4)

    def test_if_needed_rebuilds_when_the_project_address_changes(self):
        self.run_script()
        write(self.repo + "/Normie-Linux.kiwi",
              "<image><description><contact>https://github.com/a/b</contact></description></image>")
        open(self.log, "w").close()
        self.run_script("--if-needed")
        self.assertTrue(self.calls())

    def test_missing_tools_are_explained_with_the_one_install_command(self):
        # a PATH holding the ordinary tools and our fake rpmbuild, but no createrepo_c at all
        lean = self.d + "/lean"
        os.makedirs(lean)
        for tool in ("dirname", "basename", "sed", "find", "sort", "xargs", "sha256sum", "cut", "head", "cat", "tr",
                     "mktemp", "wc", "ls", "mkdir", "rm", "cp", "mv", "chmod", "tail", "echo"):
            path = shutil.which(tool)
            if path:
                os.symlink(path, f"{lean}/{tool}")
        os.symlink(self.bin + "/rpmbuild", lean + "/rpmbuild")
        r = subprocess.run([shutil.which("bash"), self.repo + "/tools/build-rpms.sh"], cwd="/",
                           env=dict(self.env, PATH=lean), capture_output=True, text=True)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sudo dnf install rpm-build createrepo_c", out)

    def test_a_failing_build_stops_and_shows_what_rpmbuild_said(self):
        rc, out = self.run_script(FAKE_RPMBUILD_FAIL="1")
        self.assertEqual(rc, 1)
        self.assertIn("failed", out)
        self.assertIn("bad spec", out)
        self.assertFalse(os.path.exists(self.local))                         # nothing half-published

    def test_unknown_option_is_refused(self):
        rc, _ = self.run_script("--frobnicate")
        self.assertEqual(rc, 2)


def read_file(path):
    with open(path) as fh:
        return fh.read()


class UpdateIsoBuildsThePackages(unittest.TestCase):
    def test_update_iso_builds_the_packages_between_the_description_check_and_the_package_checks(self):
        text = read("tools", "update-iso.sh")
        a, b, c = (text.index(x) for x in ("step 3 ", "step 4 ", "step 5 "))
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertIn("tools/build-rpms.sh --if-needed", text)
        self.assertIn('[$1/7]', text)

    def test_build_sh_makes_sure_the_packages_are_built_for_normie_images_only(self):
        text = read("tools", "build.sh")
        self.assertIn('[ "$KIWI_FILE" = "Normie-Linux.kiwi" ]', text)
        self.assertIn("build-rpms.sh\" --if-needed", text)


def make_iso(path, volume="Normie-Linux-Full-Live-45", publisher="Normie Linux contributors", application="Normie_Linux"):
    pvd = bytearray(2048)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    for off, size, val in ((40, 32, volume), (318, 128, publisher), (446, 128, ""), (574, 128, application)):
        pvd[off:off + size] = val.encode().ljust(size, b" ")
    with open(path, "wb") as fh:
        fh.write(b"\0" * 32768 + bytes(pvd))


FEDORA_KDE_PROFILE = """[Profile]
profile_id = fedora-kde
base_profile = fedora

[Profile Detection]
os_id = fedora
variant_id = kde

[Bootloader]
efi_dir = fedora
"""
NORMIE_PROFILE = FEDORA_KDE_PROFILE.replace("fedora-kde", "normie-kde").replace("os_id = fedora", "os_id = normie")


def make_image(root, name="Normie Linux", ident="normie", extra=None, profile=True):
    if profile:
        write(f"{root}/etc/anaconda/profile.d/fedora-kde.conf", FEDORA_KDE_PROFILE)
        write(f"{root}/etc/anaconda/profile.d/normie-kde.conf", NORMIE_PROFILE)
    write(f"{root}/usr/lib/os-release",
          f'NAME="{name}"\nID={ident}\nID_LIKE=fedora\nVERSION_ID=45\nPRETTY_NAME="{name} 45 (Alpha)"\nLOGO=normie-logo-icon\n'
          'HOME_URL="https://github.com/x/y"\n')
    write(f"{root}/etc/xdg/kdeglobals", "[KDE]\nLookAndFeelPackage=org.normielinux.normie.desktop\n")
    write(f"{root}/usr/share/plasma/look-and-feel/org.normielinux.normie.desktop/metadata.json", "{}")
    for rel, text in (extra or {}).items():
        write(f"{root}/{rel}", text)


class AuditBranding(unittest.TestCase):
    def run_audit(self, *args):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "audit-branding.py"), *args], capture_output=True, text=True,
                           env=dict(os.environ, NORMIE_OUT=tmpdir()))
        return r.returncode, r.stdout + r.stderr

    def setUp(self):
        self.d = tmpdir()
        self.root = self.d + "/image-root"
        self.iso = self.d + "/x.iso"
        make_iso(self.iso)

    def test_a_clean_image_passes(self):
        make_image(self.root)
        rc, out = self.run_audit("--root", self.root, "--iso", self.iso)
        self.assertEqual(rc, 0, out)
        self.assertIn("ok      os-release", out)
        self.assertIn("ok      default look-and-feel", out)
        self.assertIn("ok      installer profile normie-kde matches ID=normie (boot-loader folder EFI/fedora)", out)
        self.assertIn("0 failure(s)", out)

    def test_fedoras_os_release_fails(self):
        make_image(self.root, name="Fedora Linux", ident="fedora")
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("FAIL    os-release ID is 'fedora'", out)
        self.assertIn("still names Fedora", out)

    def test_red_hat_bug_reporting_keys_fail(self):
        make_image(self.root)
        with open(self.root + "/usr/lib/os-release", "a") as fh:
            fh.write('REDHAT_BUGZILLA_PRODUCT="Normie"\n')
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("REDHAT_BUGZILLA_PRODUCT", out)

    def test_losing_id_like_fedora_fails(self):
        make_image(self.root)
        write(self.root + "/usr/lib/os-release", read_file(self.root + "/usr/lib/os-release").replace("ID_LIKE=fedora\n", ""))
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("ID_LIKE", out)

    def test_fedoras_look_and_feel_still_the_default_fails(self):
        make_image(self.root)
        write(self.root + "/etc/xdg/kdeglobals", "[KDE]\nLookAndFeelPackage=org.fedoraproject.fedoradark.desktop\n")
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("default look-and-feel is still org.fedoraproject.fedoradark.desktop", out)

    def test_fedoras_look_and_feel_pack_being_installed_is_only_a_review_item(self):
        # plasma-workspace requires that package, so it is there; what matters is that it is not the default
        make_image(self.root, extra={"usr/share/plasma/look-and-feel/org.fedoraproject.fedora.desktop/metadata.json": "{}"})
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("REVIEW  Fedora's look-and-feel pack is installed", out)

    def test_our_look_and_feel_pack_missing_fails(self):
        make_image(self.root)
        shutil.rmtree(self.root + "/usr/share/plasma/look-and-feel/org.normielinux.normie.desktop")
        os.makedirs(self.root + "/usr/share/plasma/look-and-feel/org.kde.breeze.desktop")
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("our look-and-feel pack", out)

    def test_files_and_text_that_mention_fedora_are_listed_for_review_not_failed(self):
        make_image(self.root, extra={"usr/share/anaconda/pixmaps/fedora-logo.png": "x",
                                     "usr/share/pixmaps/about.txt": "Powered by Fedora\n",
                                     "usr/share/icons/hicolor/scalable/apps/org.fedoraproject.AnacondaInstaller.svg": "<svg/>"})
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("REVIEW  file named for Fedora: /usr/share/anaconda/pixmaps/fedora-logo.png", out)
        self.assertIn("REVIEW  mentions Fedora (1x): /usr/share/pixmaps/about.txt", out)
        self.assertNotIn("AnacondaInstaller", "".join(l for l in out.splitlines() if "REVIEW" in l))

    def test_no_installer_profile_for_our_id_fails(self):
        make_image(self.root, profile=False)
        write(self.root + "/etc/anaconda/profile.d/fedora-kde.conf", FEDORA_KDE_PROFILE)
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 1)
        self.assertIn("no installer profile matches ID=normie", out)

    def test_a_profile_with_no_boot_loader_folder_is_a_review_item(self):
        make_image(self.root, profile=False)
        write(self.root + "/etc/anaconda/profile.d/normie-kde.conf",
              "[Profile]\nprofile_id = normie-kde\n[Profile Detection]\nos_id = normie\n")
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 0, out)
        self.assertIn("no boot-loader folder", out)

    def test_expected_mentions_are_counted_and_the_rest_are_shown_with_their_lines(self):
        make_image(self.root, extra={
            "usr/share/anaconda/dbus/confs/org.fedoraproject.Anaconda.Boss.conf": "<busconfig>Fedora</busconfig>",
            "usr/share/metainfo/org.fedoraproject.dejavu-fonts.metainfo.xml": "<id>org.fedoraproject.dejavu</id>",
            "etc/anaconda/profile.d/fedora-server.conf": "profile_id = fedora-server\n",
            "usr/share/applications/liveinst.desktop": "[Desktop Entry]\nName=Install\nComment=Install Fedora to disk\n",
            "usr/share/applications/org.fedoraproject.MediaWriter.desktop": "Name=Fedora Media Writer\n"})
        rc, out = self.run_audit("--root", self.root)
        self.assertEqual(rc, 0, out)
        reviewed = "\n".join(l for l in out.splitlines() if l.startswith("REVIEW"))
        self.assertNotIn("Anaconda.Boss", reviewed)
        self.assertNotIn("dejavu", reviewed)
        self.assertNotIn("fedora-server", reviewed)
        self.assertIn("/usr/share/applications/liveinst.desktop", reviewed)       # a person could see this one
        self.assertIn("MediaWriter.desktop", reviewed)                            # a Fedora-named app
        self.assertIn("          > Comment=Install Fedora to disk", out)         # and the line is shown
        self.assertRegex(out, r"note    \d+ files: installer D-Bus names")

    def test_fedoras_publisher_on_the_iso_fails(self):
        make_iso(self.iso, publisher="Fedora Project")
        rc, out = self.run_audit("--iso", self.iso)
        self.assertEqual(rc, 1)
        self.assertIn("ISO publisher is 'Fedora Project'", out)

    def test_a_clean_iso_passes_and_a_non_iso_is_reported(self):
        rc, out = self.run_audit("--iso", self.iso)
        self.assertEqual(rc, 0, out)
        self.assertIn("Normie-Linux-Full-Live-45", out)
        write(self.d + "/junk.iso", "not an iso")
        rc, out = self.run_audit("--iso", self.d + "/junk.iso")
        self.assertEqual(rc, 1)

    def test_with_nothing_to_audit_it_says_so(self):
        rc, out = self.run_audit()
        self.assertEqual(rc, 2)
        self.assertIn("Nothing to audit", out)
        self.assertIn("not inside the virtual machine", out)      # people tried it in the VM once

    def test_the_iso_reader_matches_the_real_layout(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("audit", os.path.join(ROOT, "tools", "audit-branding.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ids = mod.read_iso_ids(self.iso)
        self.assertEqual(ids["volume id"], "Normie-Linux-Full-Live-45")
        self.assertEqual(ids["publisher"], "Normie Linux contributors")


class TryIso(unittest.TestCase):
    """tools/try-iso.sh with a fake qemu and fake firmware files."""

    def setUp(self):
        self.d = tmpdir()
        os.makedirs(self.d + "/bin")
        write(self.d + "/bin/qemu-system-x86_64", '#!/bin/bash\necho "QEMU $*" >> "$FAKE_LOG"\n', 0o755)
        write(self.d + "/bin/qemu-img", '#!/bin/bash\necho "IMG $*" >> "$FAKE_LOG"\n: > "${@: -2:1}"\n', 0o755)
        write(self.d + "/code.fd", "code")
        write(self.d + "/vars.fd", "vars")
        self.out = self.d + "/out"
        os.makedirs(self.out + "/Normie-Full-Live-build")
        write(self.out + "/Normie-Full-Live-build/Normie-Linux.iso", "iso")
        self.log = self.d + "/log"
        write(self.log, "")
        self.env = dict(os.environ, PATH=self.d + "/bin:" + os.environ["PATH"], NORMIE_OUT=self.out, FAKE_LOG=self.log,
                        NORMIE_OVMF_CODE=self.d + "/code.fd", NORMIE_OVMF_VARS=self.d + "/vars.fd")

    def run_script(self, *args):
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "try-iso.sh"), *args], env=self.env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_it_boots_the_newest_iso_with_uefi_and_a_fresh_disk(self):
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        log = read_file(self.log)
        self.assertIn("IMG create -q -f qcow2", log)
        self.assertIn("QEMU", log)
        self.assertIn("Normie-Linux.iso", log)
        self.assertIn("if=pflash", log)
        self.assertIn("bootindex=0", log)
        self.assertTrue(os.path.exists(self.out + "/vm/OVMF_VARS.fd"))

    def test_installed_mode_boots_the_disk_without_the_iso(self):
        self.run_script()
        open(self.log, "w").close()
        rc, out = self.run_script("--installed")
        self.assertEqual(rc, 0, out)
        self.assertNotIn(".iso", read_file(self.log))
        self.assertNotIn("media=cdrom", read_file(self.log))

    def test_installed_mode_without_a_disk_is_explained(self):
        rc, out = self.run_script("--installed")
        self.assertEqual(rc, 1)
        self.assertIn("no installed virtual disk", out)

    def test_fresh_throws_the_old_disk_away(self):
        self.run_script()
        write(self.out + "/vm/normie-test.qcow2", "old installation")
        open(self.log, "w").close()
        self.run_script("--fresh")
        self.assertIn("IMG create", read_file(self.log))

    def test_missing_tools_are_explained_with_the_install_command(self):
        env = dict(self.env, PATH="/nonexistent-bin", NORMIE_OVMF_CODE="/none", NORMIE_OVMF_VARS="/none")
        r = subprocess.run([shutil.which("bash"), os.path.join(ROOT, "tools", "try-iso.sh")], env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sudo dnf install qemu-system-x86 edk2-ovmf", r.stderr)

    def test_no_iso_built_yet_is_explained(self):
        os.remove(self.out + "/Normie-Full-Live-build/Normie-Linux.iso")
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn("no ISO found", out)

    def test_print_shows_the_command_and_starts_nothing(self):
        rc, out = self.run_script("--print")
        self.assertEqual(rc, 0, out)
        self.assertIn("qemu-system-x86_64", out)
        self.assertEqual(read_file(self.log), "")



class WallpaperHasNoLogo(unittest.TestCase):
    """The wallpaper once carried a small logo in its bottom-right corner; it must stay plain."""

    def test_the_wallpaper_generator_never_draws_the_logo(self):
        import ast
        src = open(os.path.join(ROOT, "packaging", "make-assets.py")).read()
        fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "wallpaper")
        calls = [c.func.id for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        self.assertNotIn("logo", calls)
        self.assertNotIn("panel", calls)


if __name__ == "__main__":
    unittest.main()
