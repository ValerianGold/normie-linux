#!/usr/bin/env python3
"""
Static sanity check for a KIWI description. No root, no network, no build.
Catches the mistakes that otherwise surface 30 minutes into a build:

  - an <include> pointing at a file that doesn't exist or isn't valid XML
  - a profile that requires / references a profile nobody defines
  - the same profile defined twice
  - an ISO volume label longer than 32 characters

Usage (from the repo root):
  python3 tools/validate-kiwi.py                       # checks Normie-Linux.kiwi
  python3 tools/validate-kiwi.py Fedora.kiwi KDE-Desktop-Live
  python3 tools/validate-kiwi.py Normie-Linux.kiwi Normie-Full-Live
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

kiwi = sys.argv[1] if len(sys.argv) > 1 else "Normie-Linux.kiwi"
want = sys.argv[2:] or (["Normie-Live", "Normie-Full-Live"] if kiwi == "Normie-Linux.kiwi" else [])

problems = []
try:
    root = ET.parse(kiwi).getroot()
except (OSError, ET.ParseError) as e:
    sys.exit(f"FAIL: cannot read {kiwi}: {e}")

files = [kiwi]
for inc in root.findall("include"):
    path = inc.get("from", "").replace("this://./", "")
    try:
        ET.parse(path)
        files.append(path)
    except (OSError, ET.ParseError) as e:
        problems.append(f"include {path}: {e}")

defined, requires, refs = {}, defaultdict(list), []
for f in files:
    try:
        r = ET.parse(f).getroot()
    except (OSError, ET.ParseError):
        continue
    for p in r.iter("profile"):
        name = p.get("name")
        if name in defined:
            problems.append(f"profile '{name}' defined twice ({defined[name]} and {f})")
        defined[name] = f
        for rq in p.findall("requires"):
            requires[name].append((rq.get("profile"), f))
    for el in r.iter():
        if el.tag != "profile" and el.get("profiles"):
            for pn in el.get("profiles").split(","):
                refs.append((pn.strip(), f, el.tag))

for name, lst in requires.items():
    for target, f in lst:
        if target not in defined:
            problems.append(f"profile '{name}' requires undefined profile '{target}' ({f})")
for pn, f, tag in refs:
    if pn not in defined:
        problems.append(f"<{tag} profiles=\"{pn}\"> uses undefined profile ({f})")

def closure(p, seen=None):
    seen = seen if seen is not None else set()
    if p in seen or p not in defined:
        return seen
    seen.add(p)
    for t, _ in requires.get(p, []):
        closure(t, seen)
    return seen

print(f"{kiwi}: {len(files)-1} include(s), {len(defined)} profile(s) defined")
for prof in want:
    if prof not in defined:
        problems.append(f"requested profile '{prof}' is not defined")
        continue
    c = sorted(closure(prof))
    print(f"\nProfile {prof} activates: {', '.join(c)}")
    try:
        out = subprocess.run(
            [sys.executable, "scripts/fedora-live-iso-label-generator", kiwi, prof],
            capture_output=True, text=True, check=True).stdout.strip()
        volid = out.split("volid,")[1]
        flag = "OK" if len(volid) <= 32 else "TOO LONG (max 32)"
        print(f"  ISO volume label: {volid} ({len(volid)} chars) {flag}")
        if len(volid) > 32:
            problems.append(f"ISO label for {prof} is {len(volid)} chars")
    except Exception as e:
        problems.append(f"label generator failed for {prof}: {e}")

print()
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("OK: no structural problems found.")
print("(This cannot check that package NAMES exist; use tools/check-packages.py for that.)")
