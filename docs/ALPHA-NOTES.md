# Normie Linux 0.1.0 alpha (source only)

This is the first public release of the **recipe** for Normie Linux: the files that build the system. **There is
no ISO to download yet.** The recipe now replaces Fedora's branding with the project's own
(`docs/REBRANDING.md`), but that has to be checked on a built system, and reviewed, before an ISO is published.

Alpha means: it works for the person who built it, it has been tried on one real machine, and it is not for
anything important.

## What works (tested on one real desktop PC with an NVIDIA RTX 3080)

- Builds with KIWI on Fedora 45; the ISO boots to a live KDE Plasma desktop and installs to disk.
- **Update & Repair:** one application that updates Fedora packages, Flathub apps and RPM Fusion packages in one
  go, re-applies the project's dependency list, and shows progress and details.
- **NVIDIA graphics driver** detected and set up automatically (the current driver branch, for Turing and newer cards).
- **Software center (Discover)** shows Fedora, Flathub, RPM Fusion, and the third-party repositories that
  Fedora offers (Google Chrome, Steam, NVIDIA). Chrome and Steam install from it.
- **Video and audio:** H.264 and H.265 play with sound.
- Common libraries are shipped (including 32-bit ones) so third-party programs and games find what they need.
  The programs themselves are not included. Xodus Nexus and a Steam game ran.

## Not tested yet

- The older NVIDIA driver branch (Maxwell, Pascal and Volta cards), Secure Boot key enrollment for the NVIDIA
  driver, laptops with two graphics chips, and installing without an internet connection.
- AMD and Intel graphics (these use Fedora's open drivers and should work, but we have not tried).
- More than one machine.

## Missing or limited

- **No ISO yet.** The rebrand (own system name, logo, wallpaper and Plasma look) is in the recipe but has not been
  audited on a built image, and the project intends to ask Fedora's legal list to look at it (recommended, not required).
- **No snapshots or rollback.** A one-click restore needs Btrfs snapshots, which are planned.
- **The tools update only by reinstalling** until the project has its own package repository. The dependency
  list does update on an installed system, because it is fetched from this repository.
- Firmware updates are off. Release upgrades (for example Fedora 45 to 46) are not built yet.

All of this is tracked in `docs/ROADMAP.md`.

## Try it

You need a Fedora 45 machine with KIWI installed. Follow `docs/START-HERE.md`; in short:

```
python3 tools/validate-kiwi.py      # fast structural check, no root needed
tools/build.sh Normie-Full-Live     # builds the full ISO
```

## Reporting problems

Use the issue forms. "An app or game will not run" is the most useful one: a missing library is usually a
one-line fix that reaches every installed system through the dependency list.
