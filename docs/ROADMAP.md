# Roadmap

Each milestone ends with something you can boot and check. Status as of the first real-hardware tests.

- [x] **M0. Project skeleton.** Repo layout, build wrapper, validators, docs.
- [x] **M1. Base ISO.** `tools/build.sh` produces an ISO that boots, installs and shows the KDE desktop.
- [x] **M2. Full ISO.** All package names resolve, DNF finds no conflicts, `Normie-Full-Live` builds and boots on real hardware; Flathub, RPM Fusion and AppStream data are set up automatically at first boot (to confirm in the software center: Chrome installs from it).
- [ ] **M3. Our own package repository** (Copr; set-up steps in `PACKAGE-REPOSITORY.md`; the scripts and the repository file in `normie-release` are in the source, the Copr account and the first publish are yours). The Update & Repair tools are now the package `normie-tools` (`packaging/normie-tools/files/`), so a fix to them also reaches installed systems (lane 3 in `ROLLING-OUT-FIXES.md`). Left: publish it, boot the new image and check an update from it.
- [ ] **M4. Update & Repair.** *(v0 works on real hardware.)* Missing: Btrfs snapshots with a one-click restore. That is also the prerequisite for turning firmware updates on. The Start menu pin moves into our own Plasma look-and-feel package (D-12, M6).
- [ ] **M5. NVIDIA hardening.** Works on one real card (RTX 3080, current branch). Still untested: the legacy 580xx branch, Secure Boot enrollment, laptops with two GPUs, installs without internet.
- [ ] **M6. Independence from Fedora's branding.** Stages R0 to R5 in `REBRANDING.md`. *(R0 to R3 are done in the source: our own release, logo, wallpaper and Plasma look packages, with the Start menu pin.)* Left: build it, run `tools/audit-branding.py`, boot it and fix what shows up, then, if you want a second opinion, ask Fedora's legal list (R4, recommended but not required). Publishing any ISO waits for the audit and a VM boot.
- [ ] **M7. Fedora release upgrades (45 to 46).** Gated by a release-channel file, per-release package lists and readiness checks (D-14).

Not milestones yet, but not forgotten: Windows-app front end (Bottles or similar), printing and scanning
checks, NTFS and exFAT drives, Bluetooth.

## Before calling it an alpha

- [x] Boots, installs, updates; NVIDIA detected and set up on real hardware; Xodus Nexus runs a game.
- [x] Sound works; H.264 plays.
- [x] H.265 plays with sound (confirmed on real hardware after the codec package fix).
- [x] Chrome and Steam show up in Discover and install from it (confirmed on real hardware).
- [ ] Confirm in Discover on a fresh install: RPM Fusion and Flathub Beta sources are enabled and the experimental apps appear.
- [ ] Source on GitHub (`docs/PUBLISHING.md`), with `tools/set-github-user.sh` run first.
- [x] Alpha notes state plainly: source only, no snapshots, installs from the 0.1.0 files cannot receive updates (`docs/ALPHA-NOTES.md`).
- [ ] For an ISO release rather than source only: finish M6 (the audit, a VM boot; Fedora's legal list is optional). M3 is wanted too, so installed systems get updates to our own packages. How to host the ISO: `DISTRIBUTING-THE-ISO.md`.
