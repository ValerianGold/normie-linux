# Design decisions

Status: **DECIDED**, **PROPOSED** (my recommendation, not yet agreed), **OPEN** (needs information).

## D-1 Base and layout: DECIDED
Fedora 45, built with KIWI. Fedora's files stay unmodified except where listed in
`docs/UPSTREAM-CHANGES.md`, and our additions live in new files. Reason: we can
pull in Fedora's fixes for each new release with a normal `git merge`. It is
not a hard rule; if a change in a Fedora file is the right fix, make it and list it.

## D-2 One ISO or one per GPU vendor: PROPOSED
One ISO that contains everything and detects hardware at first boot. Matches the
"too much beats missing" goal. The cost is ISO size (NVIDIA driver variants).

## D-3 Dependencies live in an installed metapackage: PROPOSED
A list in a KIWI file only affects the ISO at build time. For Update & Repair to
keep dependencies current, the list must exist inside the installed system:
an RPM `normie-deps` that `Requires:` everything. Planned for M3.

## D-4 Application dependency policy and Xodus Nexus: DECIDED
**Policy:** Normie Linux ships the *dependencies* popular apps need, not the apps. Anything a
user downloads should then work with no extra steps. Size is a secondary concern.

For Xodus Nexus the requirements are now documented in `docs/APP-DEPENDENCIES.md`, from two sources:
the project's own installer script and a field report of a Fedora 44 setup. Result: the prototype list
already covered almost everything; `deps.xml` gained a small labeled group. The compilers and `-devel`
packages from the field report are *not* required by the official installer (it states a compiler is not
needed for the prebuilt backend), but they stay in under the completeness policy and are harmless.

## D-5 NVIDIA: IMPLEMENTED in v0, NOT YET TESTED ON HARDWARE
Drivers are installed at run time from RPM Fusion nonfree (not bundled in the ISO). Branch per card
generation: current for Turing and newer, 580xx for Maxwell/Pascal/Volta, nouveau for older cards.
Secure Boot needs a key-enrollment step that cannot be silent. Details and limits: `UPDATE-AND-REPAIR.md`.
Still open: installs with no internet; Optimus laptops; whether to auto-offer at first login (done
as a prompt, not silently) or enable a first-boot service later.

## D-6 Update & Repair design: PARTLY IMPLEMENTED (steps 2 to 4 of 5 in v0; see UPDATE-AND-REPAIR.md)
1. Snapshot first (Btrfs; Fedora KDE already defaults to it).
2. Full system update: DNF, Flatpak, firmware.
3. Dependency health: check, then reinstall anything from `normie-deps` that is missing or damaged.
4. Rebuild and verify NVIDIA modules before declaring success.
5. Roll back automatically if any step fails.
Constraints to design around: updates apply at reboot, so the user will always see "restart to finish";
RPM Fusion's driver can lag a new Fedora kernel by days, so the kernel update may need to be held back;
Fedora 45 to 46 upgrades should be a separate, confirmed step.

## D-7 Codecs: PARTLY DECIDED
Real-hardware test: H.265 video played but without sound. Cause: only the 32-bit full-codec plugins were
listed, so 64-bit apps used Fedora's limited libraries (video was probably decoded by the NVIDIA GPU).
Decision: add RPM Fusion's `libavcodec-freeworld` (plus `gstreamer1-plugins-bad-freeworld`,
`gstreamer1-plugins-ugly`, `gstreamer1-plugin-libav`) for 64-bit. It ADDS codecs to Fedora's libraries instead of
replacing them, so no `ffmpeg` swap and no conflict. Still to verify: that H.265 audio now works.
Still open: hardware video decode on AMD and Intel needs `mesa-va-drivers-freeworld` swapped in for BOTH
architectures (a replacement, so it cannot go in the image list); a candidate for the button. The list
also still has `mesa-va-drivers-freeworld.i686` alone; `solve-check.py` reports no conflict.

## D-8 Distribution: OPEN
- Source goes on GitHub. ISOs probably cannot: as far as I know GitHub release files are
  capped at 2 GiB each (verify), and this ISO is already about 3.5 GB. Plan for another host.
- Redistribution of NVIDIA and other RPM Fusion nonfree packages must be checked before publishing.
- Fedora branding must be removed first (M6).

## D-9 Google Chrome: DECIDED
Fedora already ships the supported way to get Chrome, Steam and NVIDIA repositories: `fedora-third-party`
(GNOME asks about it at first login; KDE never does). `fedora-third-party enable` turns on the Google Chrome,
RPM Fusion Steam and NVIDIA repositories and adds Flathub, and the `fedora-appstream-metadata` package
(already in the image) is what makes them show up in a software center. `normie-sources` now runs it, once,
only when nobody has chosen yet, so a user who turned it off stays off. This gives the normal RPM Chrome,
which is also what Xodus Nexus's sign-in expects. Our own Flathub step runs first, so our Flathub remote is
unfiltered and not under Fedora's control (Fedora ships a filter hook it could narrow later).
RPM Fusion's Steam and NVIDIA repositories are shipped disabled by RPM Fusion, which is why they had to be
enabled by hand in Discover before. We do not bundle Chrome in the ISO.

## D-12 Where the Update & Repair button lives: DECIDED (pin deferred to our own look-and-feel)
Requested: a button in the Start menu next to Sleep / Restart / Shut Down. Plasma draws that row itself and
offers no way to add entries; changing it means modifying the menu's own QML, which Plasma updates would
overwrite. Agreed alternative: pin it in the Start menu's favorites, plus a reminder.
- Reminder: BUILT (`normie-remind`; also announces "Compatibility fixes are available").
- Pin: researched on the maintainer's system (Plasma 6.8.3). Favorites are NOT in the Plasma config file
  (`favoritesPortedToKAstats=true` is the only trace). They live in the activity manager's database, with their
  order in `~/.config/kactivitymanagerdrc`-style stats files, reached through the D-Bus interface
  `org.kde.ActivityManager.ResourcesLinking`. The stored form of an entry changed between Plasma versions
  (bare `app.desktop` names versus `applications:app.desktop`), a bug report against 6.8.1 shows Kickoff
  re-adding defaults after removal, and other projects need to edit the database before Plasma starts. A script
  poking that at runtime would be version-specific and could silently do nothing.
  Decision: do NOT hack it in at runtime. The correct, upgrade-safe place is the distribution's own default
  Plasma layout, which ships in a look-and-feel package. We replace Fedora's `plasma-lookandfeel-fedora` as the default
  anyway for the rebrand (M6), so the pin is added there. **Done** in `packaging/normie-lookandfeel` (its
  Kickoff setup script writes the pinned list, and its taskbar script pins it there too). It is written as a plain setting that Kickoff imports on first
  start; confirm on a fresh install that it appears. If it does not, the app is still in the menu under System and
  on the desktop, and the reminder keeps it from being forgotten.

## D-13 Snap: REMOVED
Snap was added on request, then removed by the maintainer: it adds little (nearly everything is on Flathub),
adds a background service, and the Snap Store has had scam and malware snaps. A test
(`NoSnap` in `tests/test_normie_update.py`) keeps it out.

## D-14 Fedora release upgrades (45 to 46): PLANNED, not built
Likely to break, in order of probability: third-party repositories not ready for the new release on day one
(RPM Fusion, Google); the NVIDIA driver lagging the new kernel; package names that disappear or change (the
Java 17/21 packages and compat-openssl11 vanished this way); our own tools meeting a new Python or PyQt;
interrupted upgrades. Fedora's own upgrade path is usually smooth; our additions are what raise the risk.
Plan, using GitHub for the parts that are data:
1. `dist/release-channel`: one line naming the newest Fedora release WE have verified. The button offers an
   upgrade only when this says so, so users never jump ahead of our testing. We flip it after the checks pass.
2. `dist/normie-deps-fNN.list`: a verified package list per release (`check-packages.py` and `solve-check.py`
   against that release before publishing).
3. Readiness checks before upgrading: snapshot taken, AC power, disk space, new-release repositories for
   RPM Fusion and Chrome actually exist.
4. Download, then apply at reboot (`dnf offline`), the Fedora-supported way.
5. The upgrade logic itself ships as an RPM from our own repository (Milestone 3), so a fixed upgrader runs
   BEFORE the upgrade. Scripts cannot update safely from raw GitHub (D-11).

## D-15 "Experimental" software: DECIDED (experimental apps)
Meaning confirmed: experimental **apps**, while staying inside the software center. Flathub Beta is added as a
separate Flatpak source at the lowest priority (`--prio=0`), so the stable version of an app is preferred; it
is optional and never blocks the rest of the setup. Switch off with `FLATHUB_BETA="no"` in `update.conf`.
Still to confirm in the software center: how Discover displays an app that exists in both sources.
Not enabled, on purpose: Fedora's `updates-testing` repository (pre-release system updates; the likeliest
source of breakage, and automatic updates plus no rollback make it a poor default).

## D-16 Rebranding approach: DECIDED and built (not yet checked on a built ISO)
Fork `generic-release` into our own `normie-release`, keeping `system-release`, `%fedora`/`.fc45`,
`ID_LIKE=fedora` and the service presets so Fedora's repositories and upgrades keep working; plus our own logos,
wallpaper and Plasma look. Reached the image through a build-time-only local repository (D-17), so no public
package repository is needed to build an ISO. Fedora's repository and tool packages keep their names.
Details, stages and the open legal question: `REBRANDING.md`.

## D-17 How our own packages reach the image: DECIDED
`tools/build-rpms.sh` builds `packaging/*` into `/var/lib/normie-linux/rpms`; `repositories/normie-local.xml`
hands it to KIWI (not copied into the image, unsigned packages accepted for this one repository only).
Chosen over a public repository because it works today with no accounts or keys, and over overlay files because
the package database must say Normie, not Fedora. Cost: installed systems do not receive updates to these packages
until the public repository (M3) exists.

## D-18 RPM Fusion Free codecs stay in the Full ISO: DECIDED (2026-11-24, maintainer)
The Full ISO contains about 15 packages from RPM Fusion Free (x264, x265, libde265, vvenc, aptX, the "freeworld"
GStreamer, FFmpeg and VA-API pieces) so that video and audio work out of the box. Their licences are free; Fedora
leaves them out because of software patents, which removing Fedora's name does not change. The maintainer
accepted that on purpose and can reverse it: the safe alternative is an ISO without them and an Update & Repair
step that installs them on the user's own computer. `tools/audit-branding.py` lists them. Not legal advice.

## D-19 Fedora's legal list is recommended, not required: DECIDED
The rebrand removes Fedora's trademarks and replaces them (D-16), which is what Fedora's guidelines ask of a
derivative that is not called Fedora. Asking the list about the few open points (kept `ID_LIKE=fedora` and
`%fedora`, packages whose names contain Fedora) is a precaution and does not gate publishing.
