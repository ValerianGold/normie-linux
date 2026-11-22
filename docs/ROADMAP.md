# Roadmap

Each milestone ends with something you can boot and check. Do them in order:
each one sits on top of the last.

- [x] **M0. Project skeleton.** Repo layout, build wrapper, validators, docs.
- [ ] **M1. Base ISO.** *(build completed on the maintainer's machine; still to confirm: boots to the KDE live desktop in a VM, installs)* `tools/build.sh` produces a Normie-Live ISO that boots in a VM, installs, and shows the KDE desktop.
- [ ] **M2. Full ISO.** `check-packages.py` reports zero problems and `solve-check.py` finds no conflicts; Flathub is enabled on the installed system so users can install apps (Chrome, for example) from the software center; `Normie-Full-Live` builds and boots; RPM Fusion repos also exist on the **installed** system (today they are build-time only); a 32-bit test program and a Windows program run.
- [ ] **M3. `normie-deps` package and our own repo.** The dependency list moves out of the XML into an installed RPM metapackage hosted in our own repository (Copr is the easiest start). From then on, new dependencies reach existing users through updates.
- [ ] **M4. Update & Repair.** *(v0 exists: see docs/UPDATE-AND-REPAIR.md; Btrfs snapshots with a one-click restore are the main missing part, and the prerequisite for turning firmware updates on)* One graphical button: Btrfs snapshot, full system update (DNF plus Flatpak plus firmware), dependency health check and repair, automatic rollback on failure. Updates are applied at reboot ("offline updates"). See D-6.
- [ ] **M5. NVIDIA hardening.** v0 detection and install exist (D-5); this milestone is real-hardware testing, Secure Boot, laptops with two GPUs, and offline installs.
- [ ] **M6. Independence and release.** Replace Fedora branding (`normie-release`, logos, `os-release`), choose version naming, decide ISO hosting, check redistribution licenses of nonfree packages. Only then publish ISOs. See NOTICE.md.

Things that are not milestones yet but should not be forgotten: Flathub enabled
in the software center; Windows-app front end (Bottles or similar); printing
and scanning out of the box; NTFS and exFAT drives; Bluetooth; GUI path for
the Fedora 45 to 46 upgrade (Fedora 45's end of life is about 13 months after release).

## Milestone 7: Fedora release upgrades
The button offers 45 to 46 only after we have verified it (D-14): release-channel gate, per-release package lists,
readiness checks, offline upgrade.

## Before calling it an alpha
- [x] Boots, installs, updates; NVIDIA detected and set up on real hardware; Xodus Nexus runs a game.
- [ ] H.265 sound fixed (codec patch) and verified.
- [ ] Discover shows Flathub, RPM Fusion and Snap apps out of the box (this patch) and Chrome installs from it.
- [ ] Pin in the Start menu (needs one read-only look at Plasma's config, D-12).
- [ ] Fedora branding replaced (M6) and a project contact set in `Normie-Linux.kiwi`.
- [ ] Source on GitHub; `DEPS_LIST_URL` set in `root/etc/normie/update.conf` BEFORE building any ISO that leaves your hands.
- [ ] Be clear in the alpha notes that there are no snapshots yet and that the tools update only by reinstalling until M3.
