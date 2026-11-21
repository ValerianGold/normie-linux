# Roadmap

Each milestone ends with something you can boot and check. Do them in order:
each one sits on top of the last.

- [x] **M0. Project skeleton.** Repo layout, build wrapper, validators, docs.
- [ ] **M1. Base ISO.** *(build completed on the maintainer's machine; still to confirm: boots to the KDE live desktop in a VM, installs)* `tools/build.sh` produces a Normie-Live ISO that boots in a VM, installs, and shows the KDE desktop.
- [ ] **M2. Full ISO.** `check-packages.py` reports zero problems; `Normie-Full-Live` builds and boots; RPM Fusion repos also exist on the **installed** system (today they are build-time only); a 32-bit test program and a Windows program run.
- [ ] **M3. `normie-deps` package and our own repo.** The dependency list moves out of the XML into an installed RPM metapackage hosted in our own repository (Copr is the easiest start). From then on, new dependencies reach existing users through updates.
- [ ] **M4. Update & Repair v1.** One graphical button: Btrfs snapshot, full system update (DNF plus Flatpak plus firmware), dependency health check and repair, automatic rollback on failure. Updates are applied at reboot ("offline updates"). See D-6.
- [ ] **M5. GPU detection and NVIDIA first-boot setup.** See D-5.
- [ ] **M6. Independence and release.** Replace Fedora branding (`normie-release`, logos, `os-release`), choose version naming, decide ISO hosting, check redistribution licenses of nonfree packages. Only then publish ISOs. See NOTICE.md.

Things that are not milestones yet but should not be forgotten: Flathub enabled
in the software center; Windows-app front end (Bottles or similar); printing
and scanning out of the box; NTFS and exFAT drives; Bluetooth; GUI path for
the Fedora 45 to 46 upgrade (Fedora 45's end of life is about 13 months after release).
