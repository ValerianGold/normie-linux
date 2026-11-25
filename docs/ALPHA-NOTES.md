# Normie Linux 0.1.1 alpha

This is the first public release of Normie Linux: the **recipe** that builds it (this repository) and a ready-made
**ISO**. The ISO is about 5 GB, too big for a GitHub release, so it is hosted on **SourceForge** and the
**Internet Archive**; the release page links to both and gives the SHA-256 checksum to compare after downloading.
The system carries its own name, logo, wallpaper and Plasma look instead of Fedora's (`docs/REBRANDING.md`).

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

- **The rebrand was checked by the project's own audit tool and by installing in a virtual machine.** Fedora's
  legal list has not looked at it (that is optional, and may still happen). A few harmless Fedora names remain
  where the packages require them (`docs/REBRANDING.md`).
- **The full ISO contains video and audio codecs from RPM Fusion Free** (H.264, H.265 and similar). Their licences
  are free, but some countries restrict the patents behind them. Fedora itself does not ship them
  (`docs/DISTRIBUTING-THE-ISO.md`).
- **No snapshots or rollback.** A one-click restore needs Btrfs snapshots, which are planned.
- **Our own packages** (release files, logo, wallpaper, Plasma look) update through Update & Repair, from the
  project's own package repository. **The tools themselves** (Update & Repair and its helpers) are not packaged
  yet, so a fix to them arrives only by reinstalling from a newer ISO. The dependency list updates on an
  installed system, because it is fetched from this repository.
- Firmware updates are off. Release upgrades (for example Fedora 45 to 46) are not built yet.

All of this is tracked in `docs/ROADMAP.md`.

## Try it

Download the ISO from the release page, check it against the SHA-256 checksum, and write it to a USB stick
(Fedora Media Writer, balenaEtcher or Ventoy). Start the live session first: nothing is installed until you choose to.
Try it in a virtual machine or on a computer with nothing important on it.

## Build it yourself

You need a Fedora 45 machine with KIWI installed. Follow `docs/START-HERE.md`; in short:

```
python3 tools/validate-kiwi.py      # fast structural check, no root needed
tools/build.sh Normie-Full-Live     # builds the full ISO
```

## Reporting problems

Use the issue forms. "An app or game will not run" is the most useful one: a missing library is usually a
one-line fix that reaches every installed system through the dependency list.
