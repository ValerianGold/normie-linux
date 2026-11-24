#!/usr/bin/env python3
"""
Preflight check for a KIWI description. Run on the Fedora BUILD HOST.

  1. Finds every <package name="..."/> in the given XML files and reports
     any that don't exist in the host's enabled repos (a missing package
     fails the whole KIWI build, usually 30+ minutes in).
  2. For name.i686 specs, reports packages that exist as x86_64 but have
     no i686 build (i.e. Fedora has already dropped 32-bit for them).
  3. Checks that every <signing key="file://..."/> path exists on the host
     (KIWI reads these from the host, not from the image).

Usage:
  python3 tools/check-packages.py             # defaults: components/normie/*.xml + both repo files
  python3 tools/check-packages.py FILE.xml [FILE.xml ...]
  python3 tools/check-packages.py --avail-file avail.txt FILE.xml   # skip dnf, use a saved list

Run from the repo root. Pass --save-avail FILE to also save the repo listing.

Packages we build ourselves (packaging/*/*.spec) count as available.

Before running, enable the same repos KIWI will use (Fedora, updates,
rpmfusion-free [, rpmfusion-nonfree]) on the host so RPM Fusion packages are
visible. Setup commands are in docs/START-HERE.md.
"""
import difflib
import glob
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def parse_args(argv):
    avail_file = None
    files = []
    it = iter(argv)
    for a in it:
        if a == "--avail-file":
            avail_file = next(it)
        else:
            files.append(a)
    if not files:
        files = sorted(glob.glob("components/normie/*.xml")) + [
            "repositories/core.xml", "repositories/rpmfusion.xml"]
    return avail_file, [f for f in files if os.path.exists(f)]


def load_available(avail_file):
    if avail_file:
        with open(avail_file) as fh:
            return {line.strip() for line in fh if line.strip()}
    for tool in ("dnf5", "dnf"):
        try:
            out = subprocess.run(
                [tool, "repoquery", "--available", "--arch=x86_64,i686,noarch",
                 "--queryformat", "%{name}.%{arch}\n"],
                capture_output=True, text=True, check=True,
            ).stdout
            return {line.strip() for line in out.splitlines() if line.strip()}
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    sys.exit("Could not run dnf5/dnf repoquery. Run this on the Fedora build host.")


def local_package_names():
    """Names of the packages we build ourselves (packaging/*/*.spec). They are not in any online
    repository; tools/build-rpms.sh puts them in a local one the build reads."""
    names = set()
    for spec in glob.glob("packaging/*/*.spec"):
        with open(spec) as fh:
            for line in fh:
                m = re.match(r"^Name:\s*(\S+)", line)
                if m:
                    names.add(m.group(1))
                    break
    return names


def collect(files):
    pkgs, keys = {}, {}
    for f in files:
        root = ET.parse(f).getroot()
        for p in root.iter("package"):
            name = p.get("name")
            if name:
                pkgs.setdefault(name, f)
        for s in root.iter("signing"):
            k = s.get("key", "")
            if k.startswith("file://"):
                keys.setdefault(k[len("file://"):], f)
    return pkgs, keys


def suggest(spec, names_by_arch):
    """Likely replacements for a missing package name: close spellings, plus packages
    sharing the most distinctive word (e.g. 'caladea', 'openjdk', 'liberation')."""
    base = re.sub(r"\.(i686|x86_64|noarch)$", "", spec)
    names = list(names_by_arch)
    found = difflib.get_close_matches(base, names, n=4, cutoff=0.6)
    words = [w for w in re.split(r"[-_.]", base)
             if len(w) >= 4 and not w.isdigit() and w.lower() not in
             ("fonts", "font", "devel", "libs", "runtime", "headless", "compat")]
    if words:
        key = max(words, key=len).lower()
        found += sorted(n for n in names if key in n.lower())[:6]
    out = []
    for n in found:
        if n not in out and n != base:
            out.append(n)
    return out[:6]


def main():
    avail_file, files = parse_args(sys.argv[1:])
    if not files:
        sys.exit("No input files found. Run from the project root.")
    pkgs, keys = collect(files)
    avail = load_available(avail_file)
    avail |= {f"{n}.noarch" for n in local_package_names()}
    names_by_arch = {}
    for entry in avail:
        n, _, arch = entry.rpartition(".")
        names_by_arch.setdefault(n, set()).add(arch)

    missing, no32 = [], []
    for spec, src in sorted(pkgs.items()):
        m = re.match(r"^(.*)\.(i686|x86_64|noarch)$", spec)
        if m:
            base, arch = m.groups()
            archs = names_by_arch.get(base, set())
            if arch not in archs:
                if arch == "i686" and archs:
                    no32.append((spec, src))
                else:
                    missing.append((spec, src))
        elif spec not in names_by_arch:
            missing.append((spec, src))

    print(f"Checked {len(pkgs)} package specs from {len(files)} file(s).\n")
    if missing:
        print(f"NOT FOUND in enabled repos ({len(missing)}) - these will break the build:")
        for spec, src in missing:
            print(f"  {spec:45s} ({src})")
            alts = suggest(spec, names_by_arch)
            if alts:
                print(f"      maybe you want: {', '.join(alts)}")
    else:
        print("All package names resolve.")
    if no32:
        print(f"\nEXISTS as x86_64 but NO i686 BUILD ({len(no32)}) - Fedora dropped 32-bit for these:")
        for spec, src in no32:
            print(f"  {spec:45s} ({src})")

    # Resolve $releasever / $basearch style keys using the host if possible
    rel = os.popen("rpm -E %fedora 2>/dev/null").read().strip() or "?"
    bad_keys = []
    for path, src in sorted(keys.items()):
        p = path.replace("$releasever", rel).replace("$basearch", "x86_64")
        if not os.path.exists(p):
            bad_keys.append((p, src))
    print()
    if bad_keys:
        print("SIGNING KEY FILES MISSING on this host:")
        for p, src in bad_keys:
            print(f"  {p}  ({src})")
            if "distribution-gpg-keys" in p:
                print("    -> try: sudo dnf upgrade distribution-gpg-keys")
    else:
        print("All signing key files exist.")
    sys.exit(1 if (missing or bad_keys) else 0)


if __name__ == "__main__":
    main()
