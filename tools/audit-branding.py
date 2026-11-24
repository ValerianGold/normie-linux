#!/usr/bin/env python3
"""
Search a BUILT Normie Linux image for leftover Fedora branding.

  python3 tools/audit-branding.py                    audit the newest build in ~/normie-linux-out
  python3 tools/audit-branding.py --root DIR --iso FILE

DIR is the unpacked image KIWI leaves behind (<output>/<profile>-build/build/image-root); FILE is the ISO.
Read-only; run it with sudo if it says it cannot read something.

It prints three kinds of line:
  FAIL    something that must not be there (a Fedora identity package, Fedora's name in /etc/os-release,
          Fedora's look-and-feel still the default, "Fedora" in the ISO's publisher). Exit status 1.
  REVIEW  a file or text that mentions Fedora in a branding place. Often fine (a credit, a link to Fedora's
          repositories), but look at each one. They are the list to take to Fedora's legal list (docs/REBRANDING.md R4).
  ok      checked and clean.

Fedora's repositories, keys and tools (fedora-repos, fedora-gpg-keys, fedora-third-party, ...) keep their
names on purpose: they ARE Fedora's. They are never reported.
"""
import os
import re
import subprocess
import sys

# Fedora identity / branding packages that must not be in the image
BRANDED = re.compile(r"^(fedora-release(-.*)?|fedora-logos(-.*)?|generic-(release|logos)(-.*)?|f\d+-backgrounds(-.*)?|"
                     r"desktop-backgrounds-kde|plasma-welcome-fedora|"
                     r"breeze-icon-theme-fedora|fedora-bookmarks)$")
# Packages that name Fedora because they are Fedora's own repositories and tools: fine
KEEP = re.compile(r"^(fedora-repos(-.*)?|fedora-gpg-keys|fedora-third-party|fedora-flathub-remote|"
                  r"fedora-workstation-repositories|fedora-appstream-metadata|NetworkManager-config-connectivity-fedora)$")
# Fedora's own packages require these (at exact versions), so they stay installed; reported for review
TOLERATED = ("plasma-lookandfeel-fedora", "libreport-fedora")
OURS = ("normie-release", "normie-logos", "normie-backgrounds-kde", "normie-lookandfeel")
# Branding places searched for the word "Fedora" (relative to the image root)
PLACES = ["usr/share/icons", "usr/share/pixmaps", "usr/share/plasma", "usr/share/wallpapers", "usr/share/backgrounds",
          "usr/share/anaconda", "usr/share/plymouth", "usr/share/sddm", "usr/share/kde-settings", "usr/share/applications",
          "usr/share/metainfo", "usr/share/themes", "usr/share/firefox", "etc/sddm.conf.d", "etc/xdg", "etc/skel",
          "etc/issue", "etc/issue.net", "etc/motd", "etc/anaconda", "boot", "usr/lib/os-release", "usr/lib/issue"]
# File names that must keep the word (they are identifiers owned by other software)
NAME_OK = ("org.fedoraproject.AnacondaInstaller",)
MAX_TEXT = 1_000_000


class Report:
    def __init__(self):
        self.lines = []
        self.failed = False

    def fail(self, msg):
        self.failed = True
        self.lines.append(f"FAIL    {msg}")

    def review(self, msg):
        self.lines.append(f"REVIEW  {msg}")

    def ok(self, msg):
        self.lines.append(f"ok      {msg}")

    def show(self):
        print("\n".join(self.lines))
        n_fail = sum(1 for l in self.lines if l.startswith("FAIL"))
        n_rev = sum(1 for l in self.lines if l.startswith("REVIEW"))
        print(f"\n{n_fail} failure(s), {n_rev} item(s) to review.")


def parse_os_release(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k] = v.strip().strip('"')
    return out


def audit_os_release(root, rep):
    path = os.path.join(root, "usr/lib/os-release")
    if not os.path.exists(path):
        path = os.path.join(root, "etc/os-release")
    if not os.path.exists(path):
        rep.fail("no /etc/os-release in the image")
        return
    d = parse_os_release(path)
    bad = False
    if d.get("ID") != "normie":
        rep.fail(f"os-release ID is {d.get('ID')!r}, expected 'normie'")
        bad = True
    if "fedora" not in d.get("ID_LIKE", "").split():
        rep.fail("os-release ID_LIKE no longer says fedora (tools that check ID_LIKE would stop recognising the system)")
        bad = True
    for k, v in d.items():
        if k in ("ID_LIKE", "SUPPORT_END"):
            continue
        if "fedora" in v.lower():
            rep.fail(f"os-release {k}={v!r} still names Fedora")
            bad = True
        if k.startswith("REDHAT_BUGZILLA"):
            rep.fail(f"os-release still has {k} (it sends bug reports to Red Hat)")
            bad = True
    if not bad:
        rep.ok(f"os-release: {d.get('PRETTY_NAME')} (ID={d.get('ID')}, ID_LIKE={d.get('ID_LIKE')})")


def installed_packages(root):
    try:
        out = subprocess.run(["rpm", "--root", root, "-qa", "--qf", "%{NAME}\n"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return sorted(set(out.stdout.split()))


def audit_packages(root, rep):
    pkgs = installed_packages(root)
    if not pkgs:
        rep.review("could not read the image's package list (is rpm installed here, and is this the image root?)")
        return
    branded = [p for p in pkgs if BRANDED.match(p)]
    for p in branded:
        rep.fail(f"package {p} is installed (it carries Fedora's branding)")
    for p in OURS:
        if p not in pkgs:
            rep.fail(f"our package {p} is not installed")
    for p in TOLERATED:
        if p in pkgs:
            rep.review(f"package {p} is installed because a Fedora package requires it (known leftover, see docs/REBRANDING.md)")
    others = [p for p in pkgs if "fedora" in p.lower() and not KEEP.match(p) and not BRANDED.match(p) and p not in TOLERATED]
    for p in others:
        rep.review(f"package {p} has Fedora in its name")
    if not branded:
        rep.ok(f"no Fedora identity packages among {len(pkgs)} installed packages")


def walk_places(root):
    for place in PLACES:
        base = os.path.join(root, place)
        if os.path.isfile(base):
            yield base
        elif os.path.isdir(base):
            for d, _dirs, files in os.walk(base):
                for f in files:
                    yield os.path.join(d, f)


def audit_files(root, rep):
    named, texts = [], {}
    for path in walk_places(root):
        rel = os.path.relpath(path, root)
        base = os.path.basename(path)
        if "fedora" in base.lower() and not base.startswith(NAME_OK):
            named.append(rel)
        if os.path.islink(path) or rel.endswith((".po", ".mo")):
            continue
        try:
            if os.path.getsize(path) > MAX_TEXT:
                continue
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        if b"\0" in data[:2048]:
            continue
        hits = len(re.findall(rb"fedora", data, re.I))
        if hits:
            texts[rel] = hits
    for rel in sorted(named):
        rep.review(f"file named for Fedora: /{rel}")
    for rel, n in sorted(texts.items())[:80]:
        rep.review(f"mentions Fedora ({n}x): /{rel}")
    if len(texts) > 80:
        rep.review(f"... and {len(texts) - 80} more files that mention Fedora")
    if not named and not texts:
        rep.ok("no file in the branding places is named for, or mentions, Fedora")


def audit_look_and_feel(root, rep):
    found = []
    for base in ("etc", "usr/share/kde-settings"):
        for d, _dirs, files in os.walk(os.path.join(root, base)):
            for f in files:
                p = os.path.join(d, f)
                if os.path.islink(p):
                    continue
                try:
                    with open(p, errors="ignore") as fh:
                        for line in fh:
                            m = re.match(r"\s*LookAndFeelPackage\s*=\s*(\S+)", line)
                            if m:
                                found.append((os.path.relpath(p, root), m.group(1)))
                except OSError:
                    pass
    if not found:
        rep.review("no LookAndFeelPackage setting found in /etc or /usr/share/kde-settings; check the desktop in a VM")
    for rel, value in found:
        if "fedora" in value.lower():
            rep.fail(f"default look-and-feel is still {value} (/{rel})")
        elif value == "org.normielinux.normie.desktop":
            rep.ok(f"default look-and-feel is {value} (/{rel})")
        else:
            rep.review(f"default look-and-feel is {value} (/{rel})")
    lnf = os.path.join(root, "usr/share/plasma/look-and-feel")
    if os.path.isdir(lnf):
        leftovers = [d for d in os.listdir(lnf) if "fedora" in d.lower()]
        for d in leftovers:
            rep.review(f"Fedora's look-and-feel pack is installed (listed in the theme chooser): {d}")
        if not os.path.isdir(os.path.join(lnf, "org.normielinux.normie.desktop")):
            rep.fail("our look-and-feel pack org.normielinux.normie.desktop is not installed")
    anaconda = os.path.join(root, "etc/anaconda/product.d")
    if os.path.isdir(anaconda):
        rep.review("installer product settings present (check the installer in a VM): " + ", ".join(sorted(os.listdir(anaconda))))


def read_iso_ids(path):
    """The text fields of an ISO 9660 primary volume descriptor."""
    with open(path, "rb") as fh:
        fh.seek(32768)
        pvd = fh.read(2048)
    if pvd[1:6] != b"CD001":
        raise ValueError("not an ISO 9660 image")
    field = lambda a, b: pvd[a:b].decode("ascii", "replace").strip()
    return {"volume id": field(40, 72), "publisher": field(318, 446),
            "data preparer": field(446, 574), "application": field(574, 702)}


def audit_iso(path, rep):
    try:
        ids = read_iso_ids(path)
    except (OSError, ValueError) as e:
        rep.fail(f"cannot read the ISO {path}: {e}")
        return
    bad = False
    for k, v in ids.items():
        if "fedora" in v.lower():
            rep.fail(f"ISO {k} is {v!r}")
            bad = True
    if not bad:
        rep.ok("ISO labels: " + "; ".join(f"{k}={v!r}" for k, v in ids.items() if v))


def newest(pattern_dir, suffix):
    best = None
    for d, _dirs, files in os.walk(pattern_dir):
        for f in files:
            if f.endswith(suffix):
                p = os.path.join(d, f)
                if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                    best = p
    return best


def main(argv):
    root = iso = None
    it = iter(argv)
    for a in it:
        if a == "--root":
            root = next(it, None)
        elif a == "--iso":
            iso = next(it, None)
        else:
            print(__doc__)
            return 2 if a not in ("-h", "--help") else 0
    out = os.environ.get("NORMIE_OUT", os.path.expanduser("~/normie-linux-out"))
    prof = os.path.join(out, "Normie-Full-Live-build")
    if root is None and os.path.isdir(os.path.join(prof, "build", "image-root")):
        root = os.path.join(prof, "build", "image-root")
    if iso is None and os.path.isdir(prof):
        iso = newest(prof, ".iso")
    if root is None and iso is None:
        print(f"Nothing to audit: no build found under {prof}. Pass --root DIR and/or --iso FILE.")
        return 2
    rep = Report()
    if root:
        if not os.path.isdir(root):
            print(f"Not a folder: {root}")
            return 2
        audit_os_release(root, rep)
        audit_packages(root, rep)
        audit_look_and_feel(root, rep)
        audit_files(root, rep)
    else:
        rep.review("the unpacked image folder was not found, so only the ISO labels were checked (use --root DIR)")
    if iso:
        audit_iso(iso, rep)
    rep.show()
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
