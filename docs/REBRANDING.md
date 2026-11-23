# Rebranding: becoming independent of Fedora's trademarks

Status: **planned, not started.** Publishing this source repository is fine now. Publishing an ISO that
still carries Fedora's branding is not. This document says why, what the work is, and what comes first.
(Not legal advice; Fedora's own legal list is the place to confirm the open points below.)

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
| `plasma-lookandfeel-fedora` | Default Plasma layout and look. **Our own version is where the Start menu pin goes** (D-12) |
| `plasma-welcome-fedora` | The welcome app's Fedora text and pages |
| `breeze-icon-theme-fedora` | Icon theme variant carrying Fedora's logo |
| `fedora-bookmarks` | Firefox bookmarks and start page |
| `libreport-fedora` | Sends users' crash reports to Red Hat's Bugzilla; must point at our own tracker instead |

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
2. **R1, our own package repository** (also solves lane 3 in `ROLLING-OUT-FIXES.md`). Copr is the easiest start.
3. **R2, build** `normie-release`, `normie-logos`, `normie-release-notes` (and `normie-tools` for our scripts).
   Test in a VM: boots, logs in, `dnf upgrade` works, RPM Fusion installs, `rpm -E %fedora` still prints 45.
4. **R3, swap them into the image** (`teams/kde.xml` names `fedora-release-kde` as a bootstrap package), rebuild,
   then search the whole image for the word "Fedora" in os-release, GRUB, boot splash, login screen,
   installer and wallpapers.
5. **R4, ask Fedora's legal list to review** the audit result before publishing.
6. **R5, publish** the ISO.

## What is already done

`NOTICE.md` states that Normie Linux is not affiliated with Fedora and that Fedora's branding must be
replaced before any ISO is published. `Normie-Linux.kiwi` already uses the name Normie-Linux for the image
and the ISO label. A draft logo is in `branding/` (`normie-logo.svg`).
