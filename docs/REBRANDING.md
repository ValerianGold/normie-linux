# Rebranding: becoming independent of Fedora's trademarks

Status: **built in the source (stages R0 to R3), not yet checked on a built ISO.** The recipe now builds
the image with our own release files, logos, wallpaper and Plasma look instead of Fedora's. What is left is
to build it, boot it, run the audit (`tools/audit-branding.py`) and fix what it finds (R3), then ask Fedora's
legal list (R4, recommended but not required) before an ISO is published (R5). Publishing this source repository is fine now.
(Not legal advice; Fedora's own legal list is the place to confirm the open points below.)

## How it works now

| Piece | Where | What it does |
|---|---|---|
| `normie-release` | `packaging/normie-release/` | `/etc/os-release` (`NAME="Normie Linux"`, `ID=normie`, `ID_LIKE=fedora`), the version macros, dnf defaults, login banner. Forked from Fedora's `generic-release` 45 (MIT) |
| `normie-logos` | `packaging/normie-logos/` | Our logo as the system icon and the Start button (`start-here`), the installer artwork and the boot-splash watermark |
| `normie-backgrounds-kde` | `packaging/normie-backgrounds-kde/` | The default wallpaper (also `/usr/share/wallpapers/Default`) |
| `normie-lookandfeel` | `packaging/normie-lookandfeel/` | The default Plasma look (dark Breeze, our wallpaper, our logo on the Start button) and **Update & Repair pinned in the Start menu and on the taskbar** (D-12) |

The four are built on the build host by `tools/build-rpms.sh` (needs `sudo dnf install rpm-build createrepo_c`
once) into a local repository, `/var/lib/normie-linux/rpms`, which `repositories/normie-local.xml` gives to
KIWI. It is used only while building; installed systems never see it. `tools/update-iso.sh` does this step
for you. The artwork under `packaging/*/files/` is generated from `branding/normie-logo.svg` by
`packaging/make-assets.py` and committed, so building needs no image tools.

`components/normie/branding.xml` names our packages and excludes Fedora's branded ones. Fedora's own
files stay untouched: `Normie-Live` now requires `KDE-Desktop` and `LiveInstall` (what Fedora's
`KDE-Desktop-Live` is made of) instead of `KDE-Desktop-Live` itself, because that profile names
`fedora-release-kde`. `config.sh` points the default Plasma look at ours.

Kept on purpose, because they are Fedora's repositories and tools: `fedora-repos`, `fedora-gpg-keys`,
`fedora-third-party`, `fedora-flathub-remote`, `fedora-workstation-repositories`, `fedora-appstream-metadata`,
`NetworkManager-config-connectivity-fedora`, and the `%fedora` / `.fc45` macros and `ID_LIKE=fedora`.
One name we could not change because other software owns it: the installer's launcher icon is still called
`org.fedoraproject.AnacondaInstaller` (we ship our logo under that name).

**Known leftovers (found by the dependency check):** two Fedora-branded packages stay installed because Fedora's
own packages require them. `plasma-lookandfeel-fedora`: `plasma-workspace` requires it at its exact version,
so nothing of ours can stand in for it. Our look is the default, so it only adds "Fedora" entries to the theme
chooser. `libreport-fedora`: `abrt-desktop` (crash reporting) requires it; it would send a user's crash
report to Red Hat's Bugzilla only if the user chooses to report one. To remove them for good, either drop
`abrt-desktop`, or rebuild the affected Fedora packages in our own repository (M3). Both are listed for review by
`tools/audit-branding.py`.

## Reading the audit

A built image mentions "Fedora" in hundreds of files. Almost all of them are names that other software looks
for and that we must not change: the installer's D-Bus names (`org.fedoraproject.Anaconda...`), AppStream
identifiers of fonts and language packs, the installer's profiles for other products, the kernel's build
settings and `ID_LIKE=fedora`. `tools/audit-branding.py` counts those on `note` lines and does not list them.
Every `REVIEW` line that remains is a file a person could actually see, and the audit prints the lines that
mention Fedora under it. Those are the ones to fix or take to Fedora's legal list.

After the first audit these were fixed: the lock screen wallpaper path (`/usr/share/wallpapers/Fedora/` in KDE's
defaults) and an update script that set the Start button to `start-here-kde-fedora` (both rewritten by
`config.sh`), and Fedora Media Writer (left out of the image). Still listed on purpose: Fedora's own
look-and-feel packs (see above), Konqueror's bookmarks, NeoChat's default room and the Mac boot file
`SystemVersion.plist`. Nobody sees those unless they open that particular program or boot a Mac.
`/boot/grub2/grub.cfg` inside the build folder lists the computer the build ran on (the build's os-prober found
it); the installer writes a fresh one onto the installed system, so it does not reach users.

## Known gaps to check on the first built ISO

- The installer (Anaconda) picks its settings by the system's `ID` and `VARIANT_ID`. Ours is `normie`, which no
  Fedora profile matches, so `config.sh` makes `/etc/anaconda/profile.d/normie-kde.conf` as a copy of Fedora's
  `fedora-kde.conf` while building (same settings, matched by our ID). The audit checks that it exists and shows the
  boot-loader folder (`EFI/fedora`, which must stay: the shim and GRUB packages we keep install there).
  Confirm in a VM that an installed system boots, and look at its boot-menu entry name.
- Whether the KDE settings or any other package still hard-requires something we excluded
  (`tools/solve-check.py` reports that before the long build).
- Whether `fedora-third-party` works when `ID` is not `fedora` (Update & Repair falls back to adding Flathub itself).
- The Start menu pin and the taskbar pin are written as plain settings by the look-and-feel's setup scripts; Plasma 6.8
  keeps Start menu favorites in its activity database, so confirm both appear on a fresh install.
- Text baked into the initial RAM disk (boot splash) and the GRUB menu title can only be seen by booting.

## What Fedora requires of a remix

From Fedora's trademark guidelines and its Remix page:

- The `fedora-logos`, `fedora-release` and `fedora-release-notes` packages must be **removed**. You may
  replace them with packages of your own that contain no Fedora trademarks.
- Fedora provides `generic-logos`, `generic-release` and `generic-release-notes` for this, and you may make
  your own. Replacements should provide the same capabilities (for example `system-logos`, `system-release`).
- You may call your distribution a completely different name with your own artwork. Saying it is
  *based on* Fedora is fine.
- Replacing package names alone does not always remove every trademark: text baked into other files (for
  example a boot splash stored inside the initial RAM disk) can survive, so we audit afterwards.

## Why this is more than a package swap

Fedora's identity, `/etc/os-release`, RPM macros (`%fedora`, `.fc45`), DNF defaults and **service presets**
live in `fedora-release-common` plus an identity subpackage (which ships only `os-release`). The stock
`generic-release` calls the system "Generic" and its presets differ from current Fedora's. Normie Linux
must keep working with Fedora's repositories, RPM Fusion, Flathub and Fedora upgrades, so a replacement has to
keep: `system-release(45)`, `%fedora` and `.fc45`, `ID_LIKE=fedora`, and the presets that start the login
screen, networking and the rest.

## Two ways to do it

| | A. Fork `generic-release` into `normie-release` | B. Keep `fedora-release-common`, replace only identity and logos |
|---|---|---|
| Follows Fedora's stated rules | Yes, plainly | **Unclear.** Whether keeping a package from the `fedora-release` family complies is an open question in Fedora's own forums |
| Our workload | Higher: we copy and maintain the presets and macros each release (Fedora's are MIT-licensed) | Lower |
| Recommended | **Yes, unless Fedora's legal list says B is fine** | Only with written confirmation |

Fedora's own guidelines (as read in November 2026; Fedora's site blocked automated reading, so confirm them yourself)
let anyone distribute a modified Fedora under another name once Fedora's trademarks are removed, without asking.
Asking the legal list (`legal@lists.fedoraproject.org`) is therefore a precaution about the few open points, not a gate.

## Inventory results (R0 is done)

From an installed Normie system (Fedora 45 KDE base, Plasma 6.8.3). Sorting is my judgment of Fedora's
rules; the open questions go to Fedora's legal list (stage R4).

**Must replace** (Fedora's own rule names `fedora-logos`, `fedora-release` and `fedora-release-notes`; the
`fedora-release` family is the same family):

| Package | What it carries |
|---|---|
| `fedora-release-kde-desktop`, `fedora-release-identity-kde-desktop`, `fedora-release-common` | The identity (`/etc/os-release`: `NAME="Fedora Linux"`, `ID=fedora`, `LOGO=fedora-logo-icon`, `REDHAT_BUGZILLA_*`), version macros, service presets. The image names `fedora-release-kde` (`teams/kde.xml`) |
| `fedora-logos` | Fedora's logos and boot-splash artwork |

**Should replace** (branded artwork, texts or defaults, not named in the rule but plainly Fedora's):

| Package | Why |
|---|---|
| `f45-backgrounds-base`, `f45-backgrounds-kde`, `desktop-backgrounds-kde` | Fedora's wallpapers |
| `plasma-lookandfeel-fedora` | Default Plasma layout and look. Our own version is the default and holds the Start menu pin (D-12); this package itself must stay (see the leftovers above) |
| `plasma-welcome-fedora` | The welcome app's Fedora text and pages |
| `breeze-icon-theme-fedora` | Icon theme variant carrying Fedora's logo |
| `fedora-bookmarks` | Firefox bookmarks and start page |
| `libreport-fedora` | Sends users' crash reports to Red Hat's Bugzilla if they choose to report; must point at our own tracker instead (kept for now, see the leftovers above) |

**Keep** (they name Fedora because they ARE Fedora's repositories, keys and tools; this is the "based on
Fedora" reference, not our branding): `fedora-repos`, `fedora-gpg-keys`, `fedora-third-party`,
`fedora-flathub-remote`, `fedora-workstation-repositories`, `fedora-appstream-metadata`,
`NetworkManager-config-connectivity-fedora` (consider our own check address later), `lsb_release`, and the
`rpmfusion-*` packages. Matches for "generic" such as `mingw-binutils-generic` are unrelated.

`/etc/os-release` after the rebrand: new `NAME`, `PRETTY_NAME`, `ID=normie`, `LOGO`, `HOME_URL` and support
URLs, `DEFAULT_HOSTNAME`; remove `REDHAT_BUGZILLA_*`; keep `ID_LIKE=fedora`, `VERSION_ID=45` and
`SUPPORT_END`. Risk to test: some Fedora tools may check `ID=fedora` exactly rather than `ID_LIKE`.

## Stages

1. **R0, inventory.** Done (above).
2. **R1, our own public package repository** (also solves lane 3 in `ROLLING-OUT-FIXES.md`). Copr is the
   easiest start. Not needed to build an ISO any more (the local repository does that); needed so that
   installed systems keep receiving updates to our own packages.
3. **R2, build** `normie-release`, `normie-logos`, `normie-backgrounds-kde`, `normie-lookandfeel`. **Done in the
   source**, tested without rpmbuild by `tests/test_packaging.py`. Still to do in a VM: boots, logs in,
   `dnf upgrade` works, RPM Fusion installs, `rpm -E %fedora` still prints 45.
4. **R3, swap them into the image.** **Done in the source** (`components/normie/branding.xml`). Still to do:
   build, then run `python3 tools/audit-branding.py` and look at what it prints; boot the ISO and look at
   the boot menu, the login screen, the installer and the desktop.
5. **R4, ask Fedora's legal list to review** the audit result (recommended, not required).
6. **R5, publish** the ISO.

## What is already done

`NOTICE.md` states that Normie Linux is not affiliated with Fedora. The image is named Normie-Linux, the ISO
publisher is "Normie Linux contributors", the final logo is in `branding/`, and R0 to R3 above are in the source.
