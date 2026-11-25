"""Tests for the Normie Linux packages under packaging/.

rpmbuild is not needed (and usually not installed where the tests run). Instead each spec's %install
section is run in a scratch folder, with the few RPM macros it uses filled in, and the result is
compared with the %files list: everything listed exists, nothing is left unlisted, no link dangles.
That catches the mistakes that otherwise only show up when rpmbuild runs on the build host.
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
PKG = os.path.join(ROOT, "packaging")

MACROS = {"_prefix": "/usr", "_datadir": "/usr/share", "_sysconfdir": "/etc", "_rpmconfigdir": "/usr/lib/rpm",
          "dist": ".fc45"}
HOME = "https://github.com/example/normie-linux"
# file names that contain "fedora" because another program owns the identifier
NAME_OK = ("org.fedoraproject.AnacondaInstaller.svg",)


def png_info(path):
    """(width, height, colour_type) from a PNG header; no imaging library needed."""
    import struct
    with open(path, "rb") as fh:
        head = fh.read(33)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path + " is not a PNG"
    w, h = struct.unpack(">II", head[16:24])
    return w, h, head[25]


def jpeg_size(path):
    """(width, height) from a JPEG's start-of-frame marker."""
    import struct
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:2] == b"\xff\xd8", path + " is not a JPEG"
    i = 2
    while i < len(data):
        assert data[i] == 0xFF, "bad JPEG marker"
        marker = data[i + 1]
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    raise AssertionError("no frame header in " + path)


def read(*parts):
    with open(os.path.join(*parts)) as fh:
        return fh.read()


def expand(text, macros):
    """The small subset of RPM macro syntax our specs use."""
    for _ in range(10):
        new = re.sub(r"%\{!\?(\w+):([^}]*)\}", lambda m: "" if m.group(1) in macros else m.group(2), text)
        new = re.sub(r"%\{\?(\w+)\}", lambda m: macros.get(m.group(1), ""), new)

        def plain(m):
            if m.group(1) not in macros:
                raise KeyError(f"unknown macro %{{{m.group(1)}}}")
            return macros[m.group(1)]
        new = re.sub(r"%\{(\w+)\}", plain, new)
        if new == text:
            return text
        text = new
    raise RuntimeError("macro expansion did not settle")


class Spec:
    def __init__(self, path):
        self.path = path
        self.dir = os.path.dirname(path)
        raw = read(path)
        self.macros = dict(MACROS, normie_home_url=HOME)
        for m in re.finditer(r"^%global\s+(\w+)\s+(.*)$", raw, re.M):
            self.macros[m.group(1)] = expand(m.group(2), self.macros)
        self.tags = {}
        for m in re.finditer(r"^(\w+):\s*(.*)$", raw, re.M):
            self.tags.setdefault(m.group(1), []).append(m.group(2).strip())
        for tag in ("Name", "Version", "Release"):
            self.macros[tag.lower()] = expand(self.tags[tag][0], self.macros)
        self.sections = {}
        current = "preamble"
        for line in raw.splitlines():
            m = re.match(r"^%(prep|build|install|files|changelog|description)\b", line)
            if m:
                current = m.group(1)
                self.sections.setdefault(current, [])
                continue
            self.sections.setdefault(current, []).append(line)
        self.raw = raw

    def tag(self, name):
        return [expand(v, self.macros) for v in self.tags.get(name, [])]

    @property
    def name(self):
        return self.macros["name"]

    def install(self):
        """Run %install in a scratch folder. Returns (buildroot, builddir)."""
        work = tempfile.mkdtemp(prefix="normie-spec-")
        buildroot, builddir = os.path.join(work, "root"), os.path.join(work, "build")
        os.makedirs(buildroot)
        os.makedirs(builddir)
        # what rpmbuild does: pack the folder into Source0, unpack it in the build folder (%setup -q -c)
        # and run %install there
        sources = os.path.join(work, "sources")
        packed = subprocess.run([os.path.join(ROOT, "tools", "pack-sources.sh"), self.dir, sources],
                                capture_output=True, text=True, check=True).stdout.strip()
        assert os.path.basename(packed) == expand(self.tags["Source0"][0], self.macros), "Source0 does not name the packed tarball"
        subprocess.run(["tar", "-xzf", packed, "-C", builddir], check=True)
        macros = dict(self.macros, buildroot=buildroot)
        script = expand("\n".join(self.sections["install"]), macros)
        r = subprocess.run(["bash", "-e", "-c", script], cwd=builddir, capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(f"%install of {self.name} failed:\n{script}\n{r.stdout}{r.stderr}")
        return buildroot, builddir, work

    def files_entries(self):
        """(kind, path) for each line of %files. kind is 'dir', 'license' or 'path'."""
        out = []
        for line in self.sections["files"]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line = expand(line, self.macros)
            kind = "path"
            m = re.match(r"^%(\w+)(\([^)]*\))?\s+(.*)$", line)
            if m:
                directive, rest = m.group(1), m.group(3)
                if directive == "dir":
                    kind = "dir"
                elif directive == "license" or directive == "doc":
                    kind = "license"
                elif directive in ("attr", "config", "defattr"):
                    pass
                else:
                    raise AssertionError(f"{self.name}: unhandled %files directive %{directive}")
                line = rest
            out.append((kind, line))
        return out


def all_specs():
    return sorted(glob.glob(os.path.join(PKG, "*", "*.spec")))


def tree(buildroot):
    """Every file and link under buildroot, as '/absolute/path' strings (directories excluded)."""
    found = []
    for d, dirs, files in os.walk(buildroot):
        for name in files + [x for x in dirs if os.path.islink(os.path.join(d, x))]:
            found.append("/" + os.path.relpath(os.path.join(d, name), buildroot))
    return sorted(found)


class EverySpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = [Spec(p) for p in all_specs()]
        cls.built = {}
        for s in cls.specs:
            cls.built[s.name] = s.install()
        atexit_dirs = [b[2] for b in cls.built.values()]
        cls._cleanup = atexit_dirs

    @classmethod
    def tearDownClass(cls):
        for d in cls._cleanup:
            shutil.rmtree(d, ignore_errors=True)

    def test_there_are_exactly_the_four_packages(self):
        self.assertEqual(sorted(s.name for s in self.specs),
                         ["normie-backgrounds-kde", "normie-logos", "normie-lookandfeel", "normie-release"])

    def test_each_folder_is_named_after_its_package(self):
        for s in self.specs:
            self.assertEqual(os.path.basename(s.dir), s.name)
            self.assertEqual(os.path.basename(s.path), s.name + ".spec")

    def test_every_package_is_noarch_and_has_a_licence_and_summary(self):
        for s in self.specs:
            self.assertEqual(s.tag("BuildArch"), ["noarch"], s.name)
            self.assertTrue(s.tag("License")[0], s.name)
            self.assertTrue(s.tag("Summary")[0], s.name)

    def test_everything_listed_in_files_exists(self):
        for s in self.specs:
            buildroot, builddir, _ = self.built[s.name]
            for kind, path in s.files_entries():
                if kind == "license":
                    self.assertTrue(glob.glob(os.path.join(builddir, path)), f"{s.name}: %license/%doc {path}")
                else:
                    hits = glob.glob(buildroot + path) or ([buildroot + path] if os.path.lexists(buildroot + path) else [])
                    self.assertTrue(hits, f"{s.name}: %files lists {path} but %install did not create it")

    def test_nothing_installed_is_left_out_of_files(self):
        for s in self.specs:
            buildroot, _, _ = self.built[s.name]
            covered_dirs, covered = [], set()
            for kind, path in s.files_entries():
                if kind != "path":
                    continue
                for hit in glob.glob(buildroot + path):
                    rel = "/" + os.path.relpath(hit, buildroot)
                    if os.path.isdir(hit) and not os.path.islink(hit):
                        covered_dirs.append(rel)
                    covered.add(rel)
            unlisted = [f for f in tree(buildroot)
                        if f not in covered and not any(f.startswith(d + "/") for d in covered_dirs)]
            self.assertEqual(unlisted, [], f"{s.name}: installed but not in %files")

    def test_no_link_dangles(self):
        for s in self.specs:
            buildroot, _, _ = self.built[s.name]
            for path in tree(buildroot):
                full = buildroot + path
                if not os.path.islink(full):
                    continue
                target = os.readlink(full)
                resolved = os.path.normpath(os.path.join(os.path.dirname(path), target)) if not target.startswith("/") else target
                self.assertTrue(os.path.lexists(buildroot + resolved), f"{s.name}: {path} -> {target} points at nothing")

    def test_no_installed_file_is_named_for_fedora_except_the_installer_icon(self):
        for s in self.specs:
            buildroot, _, _ = self.built[s.name]
            for path in tree(buildroot):
                if "fedora" in os.path.basename(path).lower():
                    self.assertIn(os.path.basename(path), NAME_OK, f"{s.name}: {path}")

    def test_no_installed_text_mentions_fedora_except_where_it_is_the_truth(self):
        # the release package says "ID_LIKE=fedora" and keeps Fedora's repositories; nothing else may
        allowed = {"normie-release": {"/usr/lib/os-release", "/usr/lib/rpm/macros.d/macros.dist",
                                      "/usr/share/dnf/plugins/copr.vendor.conf",
                                      "/etc/yum.repos.d/normie.repo"}}   # the Copr web address
        for s in self.specs:
            buildroot, _, _ = self.built[s.name]
            for path in tree(buildroot):
                full = buildroot + path
                if os.path.islink(full):
                    continue
                with open(full, "rb") as fh:
                    data = fh.read()
                if b"\0" in data[:2048]:
                    continue
                if re.search(rb"fedora", data, re.I):
                    self.assertIn(path, allowed.get(s.name, set()), f"{s.name}: {path} mentions Fedora")

    def test_changelog_dates_are_real(self):
        for s in self.specs:
            entries = [l for l in s.sections["changelog"] if l.startswith("*")]
            self.assertTrue(entries, s.name)
            for l in entries:
                m = re.match(r"^\* (\w{3}) (\w{3}) (\d+) (\d{4}) ", l)
                self.assertTrue(m, l)
                d = datetime.datetime.strptime(f"{m.group(2)} {m.group(3)} {m.group(4)}", "%b %d %Y")
                self.assertEqual(d.strftime("%a"), m.group(1), f"{s.name}: bad weekday in '{l}'")

    def test_the_spec_files_do_not_use_macros_this_test_cannot_check(self):
        for s in self.specs:
            expand("\n".join(s.sections["install"] + s.sections["files"]),
                   dict(s.macros, buildroot="/x"))


class ReleasePackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = Spec(os.path.join(PKG, "normie-release", "normie-release.spec"))
        cls.root, _, cls.work = cls.spec.install()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def osrel(self):
        d = {}
        for line in read(self.root, "usr/lib/os-release").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k] = v.strip('"')
        return d

    def test_the_version_matches_the_image_description(self):
        release = ET.parse(os.path.join(ROOT, "Normie-Linux.kiwi")).getroot().findtext("preferences/release-version")
        self.assertEqual(self.spec.macros["version"], release.strip())
        self.assertEqual(self.osrel()["VERSION_ID"], release.strip())

    def test_os_release_names_normie_but_stays_fedora_compatible(self):
        d = self.osrel()
        self.assertEqual(d["NAME"], "Normie Linux")
        self.assertEqual(d["ID"], "normie")
        self.assertEqual(d["ID_LIKE"], "fedora")
        self.assertEqual(d["LOGO"], "normie-logo-icon")
        self.assertTrue(d["PRETTY_NAME"].startswith("Normie Linux 45"))

    def test_os_release_has_no_fedora_or_red_hat_leftovers(self):
        d = self.osrel()
        for k, v in d.items():
            if k != "ID_LIKE":
                self.assertNotIn("fedora", v.lower(), k)
            self.assertFalse(k.startswith("REDHAT_BUGZILLA"), k)
        self.assertNotIn("bugzilla.redhat.com", read(self.root, "usr/lib/os-release"))

    def test_os_release_urls_use_the_project_address(self):
        d = self.osrel()
        self.assertEqual(d["HOME_URL"], HOME)
        self.assertEqual(d["BUG_REPORT_URL"], HOME + "/issues")
        self.assertNotIn("@", read(self.root, "usr/lib/os-release"))                  # every placeholder was filled

    def test_without_a_project_address_it_falls_back_to_github_dot_com(self):
        spec = Spec(self.spec.path)
        spec.macros.pop("normie_home_url")
        spec.macros["home_url"] = expand("%{?normie_home_url}%{!?normie_home_url:https://github.com}", spec.macros)
        root, _, work = spec.install()
        try:
            self.assertIn('HOME_URL="https://github.com"', read(root, "usr/lib/os-release"))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_the_fedora_version_macros_survive_so_rpm_fusion_and_copr_keep_working(self):
        text = read(self.root, "usr/lib/rpm/macros.d/macros.dist")
        self.assertRegex(text, r"(?m)^%fedora\s+45$")
        self.assertRegex(text, r"(?m)^%fc45\s+1$")
        self.assertRegex(text, r"(?m)^%dist\s")
        self.assertRegex(text, r"(?m)^%dist_name\s+Normie Linux$")
        self.assertNotIn("@HOME_URL@", text)
        self.assertEqual(text.count("%dist_home_url"), 1)

    def test_the_etc_links_point_at_real_files(self):
        for name in ("os-release", "system-release", "redhat-release", "issue", "issue.net", "normie-release", "system-release-cpe"):
            self.assertTrue(os.path.exists(os.path.join(self.root, "etc", name)), name)
        self.assertIn("Normie Linux release 45", read(self.root, "etc/system-release"))

    def test_it_replaces_fedoras_release_packages_and_keeps_fedoras_repositories(self):
        s = self.spec
        for needed in ("system-release", "system-release(45)"):
            self.assertTrue(any(p.startswith(needed) for p in s.tag("Provides")), needed)
        for conflicting in ("fedora-release", "fedora-release-common", "fedora-release-identity", "generic-release"):
            self.assertIn(conflicting, s.tag("Conflicts"))
        self.assertIn("fedora-repos(45)", s.tag("Requires"))
        self.assertIn("distribution-systemd-presets", s.tag("Requires"))

    def test_dnf_defaults_do_not_block_vendor_changes(self):
        # RPM Fusion swaps (e.g. ffmpeg-free -> ffmpeg) need dnf to allow a change of vendor
        text = read(self.root, "usr/share/dnf5/libdnf.conf.d/20-defaults.conf")
        self.assertNotIn("allow_vendor_change=False", text)
        self.assertIn("pkg_gpgcheck=True", text)

    def test_plasma_desktop_stays_protected(self):
        self.assertIn("plasma-desktop", read(self.root, "etc/dnf/protected.d/normie-desktop.conf").split())


class ArtworkPackages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = {}
        for name in ("normie-logos", "normie-backgrounds-kde", "normie-lookandfeel"):
            spec = Spec(os.path.join(PKG, name, name + ".spec"))
            cls.built[name] = (spec,) + spec.install()

    @classmethod
    def tearDownClass(cls):
        for b in cls.built.values():
            shutil.rmtree(b[3], ignore_errors=True)

    def test_the_logo_package_provides_what_fedoras_logo_package_provided(self):
        spec = self.built["normie-logos"][0]
        provides = " ".join(spec.tag("Provides"))
        self.assertIn("system-logos", provides)
        self.assertIn("redhat-logos", provides)
        for c in ("fedora-logos", "generic-logos"):
            self.assertIn(c, spec.tag("Conflicts"))

    def test_the_start_button_icon_is_ours(self):
        _, root, _, _ = self.built["normie-logos"]
        svg = os.path.join(root, "usr/share/icons/hicolor/scalable/apps/start-here.svg")
        self.assertEqual(os.path.realpath(svg), os.path.realpath(os.path.join(os.path.dirname(svg), "normie-logo-icon.svg")))
        with open(os.path.join(ROOT, "branding", "normie-logo.svg"), "rb") as a, \
                open(os.path.join(root, "usr/share/icons/hicolor/scalable/apps/normie-logo-icon.svg"), "rb") as b:
            self.assertEqual(a.read(), b.read(), "the packaged logo differs from branding/normie-logo.svg; run packaging/make-assets.py")
        for size in (16, 22, 24, 32, 36, 48, 64, 96, 128, 256):
            self.assertTrue(os.path.exists(f"{root}/usr/share/icons/hicolor/{size}x{size}/places/start-here.png"), size)
        self.assertTrue(os.path.exists(f"{root}/usr/share/icons/hicolor/scalable/places/start-here.svg"))
        self.assertTrue(os.path.exists(f"{root}/usr/share/icons/hicolor/scalable/apps/kmenu.svg"))

    def test_the_icon_png_sizes_are_right(self):
        _, root, _, _ = self.built["normie-logos"]
        for size in (16, 22, 24, 32, 36, 48, 64, 96, 128, 256):
            w, h, colour = png_info(f"{root}/usr/share/icons/hicolor/{size}x{size}/apps/normie-logo-icon.png")
            self.assertEqual((w, h), (size, size))
            self.assertEqual(colour, 6, "icons need an alpha channel (RGBA)")

    def test_the_installer_images_have_the_sizes_the_installer_expects(self):
        _, root, _, _ = self.built["normie-logos"]
        expected = {"anaconda_header.png": (800, 88), "topbar-bg.png": (1040, 132), "sidebar-bg.png": (406, 767),
                    "sidebar-logo.png": (128, 128)}
        for name, size in expected.items():
            self.assertEqual(png_info(f"{root}/usr/share/anaconda/pixmaps/{name}")[:2], size, name)
        self.assertEqual(png_info(f"{root}/usr/share/anaconda/boot/splash.png")[:2], (416, 265))
        self.assertEqual(png_info(f"{root}/usr/share/anaconda/boot/syslinux-splash.png")[:2], (640, 300))

    def test_the_wallpaper_package_provides_the_capabilities_and_a_default(self):
        spec, root, _, _ = self.built["normie-backgrounds-kde"]
        provides = " ".join(spec.tag("Provides"))
        self.assertIn("system-backgrounds-kde", provides)
        self.assertIn("desktop-backgrounds-kde", provides)
        self.assertEqual(os.readlink(f"{root}/usr/share/wallpapers/Default"), "Normie")
        meta = json.loads(read(root, "usr/share/wallpapers/Normie/metadata.json"))
        self.assertEqual(meta["KPackageStructure"], "Wallpaper/Images")
        self.assertEqual(meta["KPlugin"]["Id"], "Normie")

    def test_the_wallpaper_images_are_real_pictures_of_the_right_size(self):
        _, root, _, _ = self.built["normie-backgrounds-kde"]
        for name in ("1920x1080", "3840x2160"):
            self.assertEqual("%dx%d" % jpeg_size(f"{root}/usr/share/wallpapers/Normie/contents/images/{name}.jpg"), name)

    def test_the_look_and_feel_pack_is_complete_and_selects_our_wallpaper(self):
        spec, root, _, _ = self.built["normie-lookandfeel"]
        pack = f"{root}/usr/share/plasma/look-and-feel/org.normielinux.normie.desktop"
        meta = json.loads(read(pack, "metadata.json"))
        self.assertEqual(meta["KPackageStructure"], "Plasma/LookAndFeel")
        self.assertEqual(meta["KPlugin"]["Id"], "org.normielinux.normie.desktop")
        self.assertEqual(os.path.basename(pack), meta["KPlugin"]["Id"])
        defaults = read(pack, "contents/defaults")
        self.assertIn("[Wallpaper]\nImage=Normie", defaults)
        self.assertNotIn("fedora", defaults.lower())
        for f in ("layouts/org.kde.plasma.desktop-layout.js", "plasmoidsetupscripts/org.kde.plasma.kickoff.js",
                  "plasmoidsetupscripts/org.kde.plasma.kicker.js", "plasmoidsetupscripts/org.kde.plasma.kickerdash.js",
                  "previews/preview.png"):
            self.assertTrue(os.path.exists(f"{pack}/contents/{f}"), f)
        # a fixed Provides cannot satisfy plasma-workspace's exact-version requirement, so we do not pretend to
        self.assertNotIn("plasma-lookandfeel-fedora", " ".join(spec.tag("Provides")))

    def test_the_wallpaper_the_look_and_feel_names_is_the_one_we_ship(self):
        _, root, _, _ = self.built["normie-backgrounds-kde"]
        _, lroot, _, _ = self.built["normie-lookandfeel"]
        image = re.search(r"\[Wallpaper\]\nImage=(\S+)", read(lroot, "usr/share/plasma/look-and-feel/org.normielinux.normie.desktop/contents/defaults")).group(1)
        self.assertTrue(os.path.isdir(f"{root}/usr/share/wallpapers/{image}"))

    def test_the_start_menu_setup_script_uses_our_icon_and_pins_update_and_repair(self):
        _, lroot, _, _ = self.built["normie-lookandfeel"]
        js = read(lroot, "usr/share/plasma/look-and-feel/org.normielinux.normie.desktop/contents/plasmoidsetupscripts/org.kde.plasma.kickoff.js")
        self.assertIn('writeConfig("icon", "start-here")', js)
        self.assertIn("normie-update.desktop", js)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "root", "usr", "share", "applications", "normie-update.desktop")))

    def test_update_and_repair_is_also_pinned_on_the_taskbar(self):
        _, lroot, _, _ = self.built["normie-lookandfeel"]
        js = read(lroot, "usr/share/plasma/look-and-feel/org.normielinux.normie.desktop/contents/plasmoidsetupscripts/org.kde.plasma.icontasks.js")
        self.assertIn('"applications:normie-update.desktop"', js)
        self.assertIn('writeConfig("launchers"', js)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_the_plasma_scripts_are_valid_javascript(self):
        _, lroot, _, _ = self.built["normie-lookandfeel"]
        pack = f"{lroot}/usr/share/plasma/look-and-feel/org.normielinux.normie.desktop/contents"
        for f in glob.glob(pack + "/plasmoidsetupscripts/*.js") + glob.glob(pack + "/layouts/*.js"):
            r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f + r.stderr)


class Artwork(unittest.TestCase):
    def test_the_artwork_is_original_not_copied_from_fedora(self):
        # the generator draws everything from our own SVG; its code (not its explanation) never names Fedora
        import ast
        tree_ = ast.parse(read(PKG, "make-assets.py"))
        tree_.body = tree_.body[1:]                                # drop the module docstring
        self.assertNotIn("fedora", ast.unparse(tree_).lower())

    def test_the_source_tree_has_no_files_named_for_fedora_under_packaging(self):
        for d, _dirs, files in os.walk(PKG):
            for f in files:
                self.assertNotIn("fedora", f.lower(), os.path.join(d, f))


if __name__ == "__main__":
    unittest.main()
