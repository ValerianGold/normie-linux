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
`gstreamer1-plugins-ugly`, `gstreamer1-libav`) for 64-bit. It ADDS codecs to Fedora's libraries instead of
replacing them, so no `ffmpeg` swap and no conflict. Still to verify: that H.265 audio now works.
Still open: hardware video decode on AMD and Intel needs `mesa-va-drivers-freeworld` swapped in for BOTH
architectures (a replacement, so it cannot go in the image list); a candidate for the button. The list
also still has `mesa-va-drivers-freeworld.i686` alone; `solve-check.py` reports no conflict.

## D-8 Distribution: OPEN
- Source goes on GitHub. ISOs probably cannot: as far as I know GitHub release files are
  capped at 2 GiB each (verify), and this ISO is already about 3.5 GB. Plan for another host.
- Redistribution of NVIDIA and other RPM Fusion nonfree packages must be checked before publishing.
- Fedora branding must be removed first (M6).

## D-9 Google Chrome: PARTLY DECIDED
Chrome is not in Fedora's repositories and Discover did not list it in the first VM test. Fix in place:
Flathub is now enabled automatically, which gives Discover a full catalog including Chrome (Flatpak).
Open: Xodus Nexus needs Chrome for passkey sign-in and may expect the normal (RPM) Chrome rather than the
Flatpak one. TEST both with Nexus's sign-in before choosing which one to recommend. Downloading Google's
`.rpm` and double-clicking it already works (it opens the software center and also adds Google's repository
so Chrome then updates with everything else). KDE draws `.rpm` files with an archive-style icon because it
treats them as archives, which is cosmetic.
We do not bundle Chrome in the ISO (redistribution terms are Google's to grant).

## D-12 Where the Update & Repair button lives: PARTLY BUILT
Requested: a button in the Start menu next to Sleep / Restart / Shut Down. Plasma draws that row itself and
offers no way to add entries; adding one means modifying the menu's own QML, which Plasma updates would
overwrite on machines we update automatically. Agreed alternative: pin it at the top of the Start menu
(favorites) plus a periodic reminder.
- Reminder: BUILT (`normie-remind`, see UPDATE-AND-REPAIR.md).
- Pin: NOT built. A wrong guess here could wipe the user's default favorites, so it waits for a look at how
  this Plasma version stores them (`grep -rn favorites ~/.config/plasma-org.kde.plasma.desktop-appletsrc`
  on an installed system).

## D-13 Snap: DECIDED (by the maintainer), with known trade-offs
Enabled out of the box (`snapd`, `plasma-discover-snap`, socket enabled). Known trade-offs: the Snap Store has
had scam and malware snaps (Flathub has verified publishers, the Snap Store less so); `snapd` adds a
background service and many small mounts; most apps are on Flathub anyway, so Snap mostly duplicates it. To
remove it: delete `snapd` and `plasma-discover-snap` from `components/normie/tools.xml` and the two snap
symlinks under `root/` (`root/snap` and `root/etc/systemd/system/sockets.target.wants/snapd.socket`).

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

## D-15 "Experimental" software sources: OPEN
Not enabled: Fedora's `updates-testing` repository. It delivers updates before they are tested and is the
likeliest source of breakage; combined with one-click automatic updates and no rollback it is the wrong
default for non-technical users. Candidates that are safer: Flathub Beta (a separate, clearly labeled
Flatpak source), COPR repositories chosen one by one. Needs the maintainer to say what was meant.
