# Roadmap

Each milestone ends with something you can boot and check. Status as of the first real-hardware tests.

- [x] **M0. Project skeleton.** Repo layout, build wrapper, validators, docs.
- [x] **M1. Base ISO.** `tools/build.sh` produces an ISO that boots, installs and shows the KDE desktop.
- [x] **M2. Full ISO.** All package names resolve, DNF finds no conflicts, `Normie-Full-Live` builds and boots on real hardware; Flathub, RPM Fusion and AppStream data are set up automatically at first boot (to confirm in the software center: Chrome installs from it).
- [ ] **M3. Our own package repository** (Copr is the easiest start). Needed for two things at once: (a) the Update & Repair tools update on installed systems without a reinstall (lane 3 in `ROLLING-OUT-FIXES.md`), (b) a home for `normie-release` and friends (M6). First package: `normie-tools` (the contents of `root/`).
- [ ] **M4. Update & Repair.** *(v0 works on real hardware.)* Missing: Btrfs snapshots with a one-click restore. That is also the prerequisite for turning firmware updates on. Also planned: the Start menu pin (D-12).
- [ ] **M5. NVIDIA hardening.** Works on one real card (RTX 3080, current branch). Still untested: the legacy 580xx branch, Secure Boot enrollment, laptops with two GPUs, installs without internet.
- [ ] **M6. Independence from Fedora's branding.** Stages R0 to R5 in `REBRANDING.md`. Needs M3. Publishing any ISO waits for this.
- [ ] **M7. Fedora release upgrades (45 to 46).** Gated by a release-channel file, per-release package lists and readiness checks (D-14).

Not milestones yet, but not forgotten: Windows-app front end (Bottles or similar), printing and scanning
checks, NTFS and exFAT drives, Bluetooth.

## Before calling it an alpha

- [x] Boots, installs, updates; NVIDIA detected and set up on real hardware; Xodus Nexus runs a game.
- [x] Sound works; H.264 plays.
- [ ] H.265 sound verified after the codec patch.
- [ ] Discover shows Flathub, RPM Fusion and experimental apps, and Chrome installs from it.
- [ ] Source on GitHub (`docs/PUBLISHING.md`), with `tools/set-github-user.sh` run first.
- [ ] Alpha notes state plainly: source only, no snapshots, tools update only by reinstalling until M3.
- [ ] For an ISO release rather than source only: M3 and M6 first.
