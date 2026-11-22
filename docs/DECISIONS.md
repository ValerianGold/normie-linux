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

## D-7 Codecs: OPEN
`deps.xml` lists `libavcodec-free*.i686` (Fedora's limited ffmpeg libraries). The usual way
to get full codecs is RPM Fusion's `ffmpeg` (swapping out Fedora's `ffmpeg-free`), which
conflicts with them; an alternative is RPM Fusion's `libavcodec-freeworld`, which adds codecs to
Fedora's libraries instead. Which approach (and whether 32-bit versions exist) has to be
settled by testing in M2. Related: the list also has `mesa-va-drivers-freeworld.i686` without a 64-bit
counterpart; a consistent system swaps both. `tools/solve-check.py` will show whether the current mix conflicts.
The general rules for avoiding conflicts are in `DEPENDENCY-POLICY.md`.

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

## D-12 Where the Update & Repair button lives: OPEN
Requested: a button in the Start menu next to Sleep / Restart / Shut Down. Plasma's menu draws that row
itself and offers no way to add entries to it. Adding one means modifying the menu's own QML files, and
Plasma updates would overwrite the change (or break it) on the same machines we update automatically.
Alternatives that still keep the desktop clean and the button impossible to forget:
(1) pin it as a favorite at the top of the Start menu; (2) a panel or tray icon; (3) a periodic reminder
notification ("last updated 14 days ago") with an Update now button. Needs one read-only look at how this
Plasma version stores menu favorites before writing it. Not built.
