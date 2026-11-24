#!/usr/bin/env python3
"""
Conflict check: ask DNF to resolve a profile's COMPLETE package set into an empty
install root, without installing anything. Finds package conflicts, missing
dependencies and "cannot install both X and Y" problems in about a minute,
instead of 30 minutes into a KIWI build.

check-packages.py answers "do these names exist?". This answers "can they all be
installed TOGETHER?". Run both before building the full ISO.

Usage (from the repo root, on the Fedora build host):
  sudo python3 tools/solve-check.py                       # profile Normie-Full-Live
  sudo python3 tools/solve-check.py Normie-Live           # the plain base, as a control
  python3 tools/solve-check.py --print-only Normie-Full-Live   # just show the dnf command

Run it for Normie-Live first: that set is known to build, so it proves the tool
itself works on your machine. Then run it for Normie-Full-Live.

It approximates KIWI (same repos via the host config, weak dependencies on, same
package list, same excluded packages) but is not identical. Treat a clean result
as strong evidence, not a guarantee. The full dnf output is saved to solve-check.log.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict

args = [a for a in sys.argv[1:] if not a.startswith("--")]
print_only = "--print-only" in sys.argv
profile = args[0] if args else "Normie-Full-Live"
kiwi = "Fedora.kiwi" if profile == "KDE-Desktop-Live" else "Normie-Linux.kiwi"

root = ET.parse(kiwi).getroot()
files = [kiwi] + [i.get("from").replace("this://./", "") for i in root.findall("include")]
requires = defaultdict(list)
trees = []
for f in files:
    r = ET.parse(f).getroot()
    trees.append(r)
    for p in r.iter("profile"):
        for q in p.findall("requires"):
            requires[p.get("name")].append(q.get("profile"))

active = set()
def walk(p):
    if p not in active:
        active.add(p)
        for q in requires.get(p, []):
            walk(q)
walk(profile)

specs, excludes = [], []
for r in trees:
    for pk in r.iter("packages"):
        profs = pk.get("profiles")
        if profs is not None and not (active & {x.strip() for x in profs.split(",")}):
            continue
        if pk.get("type") not in ("image", "bootstrap"):
            continue
        for c in pk:
            if c.get("arch") not in (None, "x86_64"):
                continue
            n = c.get("name")
            if c.tag == "package":
                specs.append(n)
            elif c.tag == "namedCollection":
                specs.append("@" + n)
            elif c.tag == "ignore":
                excludes.append(n)

specs = sorted(set(specs))
excludes = sorted(set(excludes))
release = (root.findtext("preferences/release-version") or "45").strip()

# Our own packages (packaging/*) come from the local repository tools/build-rpms.sh makes
local_repo = os.environ.get("NORMIE_LOCAL_REPO", "/var/lib/normie-linux/rpms")
uses_local = any(e.get("alias") == "normie-local" for r in trees for e in r.iter("repository"))

tmp = tempfile.mkdtemp(prefix="normie-solve-")
cmd = ["dnf5", f"--installroot={tmp}", f"--releasever={release}", "--use-host-config",
       "install", "--assumeno", "--setopt=install_weak_deps=True"]
if uses_local:
    cmd.insert(1, f"--repofrompath=normie-local,file://{local_repo}")
if excludes:
    cmd.append("--exclude=" + ",".join(excludes))
cmd += specs

print(f"Profile {profile}: {len(specs)} package specs, {len(excludes)} excluded, release {release}")
if print_only:
    print(" ".join(cmd[:8]), "... (+", len(specs), "specs)")
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0)
if os.geteuid() != 0:
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit("Run with sudo (dnf needs root to create the install root).")

if uses_local:
    # build (or refresh) our own packages first; does nothing if they are already up to date
    here = os.path.dirname(os.path.abspath(__file__))
    built = subprocess.run(["bash", os.path.join(here, "build-rpms.sh"), "--if-needed"])
    if built.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit("Could not build the Normie packages (see above), so the package set cannot be checked.")

print("Resolving (this downloads repository metadata, not packages)...\n")
res = subprocess.run(cmd, capture_output=True, text=True)
out = res.stdout + res.stderr
shutil.rmtree(tmp, ignore_errors=True)
with open("solve-check.log", "w") as fh:
    fh.write(out)

problem = re.search(r"Problem|Failed to resolve|cannot install both|conflicts with|nothing provides|No match for argument", out)
summary = "Transaction Summary" in out
if problem:
    print("PROBLEMS FOUND. The relevant lines:\n")
    keep = [l for l in out.splitlines()
            if re.search(r"Problem|cannot install|conflicts|nothing provides|No match|requires|package .* from", l)]
    print("\n".join(keep[:60]))
    only_missing = all(l.startswith("No match for argument") for l in keep) and keep
    if only_missing:
        print("\nThese are all MISSING package names. DNF stops at those before it can look for")
        print("conflicts, so this run says nothing about conflicts yet. Fix the names first")
        print("(python3 tools/check-packages.py shows suggestions), then run this again.")
    print("\nFull output: solve-check.log   (paste me the lines above, or that file's contents)")
    sys.exit(1)
if summary:
    m = re.search(r"Installing:?\s+(\d+)\s+packages?", out)
    print("OK: DNF can resolve the whole set with no conflicts.")
    if m:
        print(f"    ({m.group(1)} top-level installs; full detail in solve-check.log)")
    sys.exit(0)
print("INCONCLUSIVE: dnf did not print a transaction summary or a clear error.")
print("Last lines of output:\n" + "\n".join(out.splitlines()[-25:]))
print("\nFull output: solve-check.log. Paste me this and I will adjust the tool.")
sys.exit(2)
