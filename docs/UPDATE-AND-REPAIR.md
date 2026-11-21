# Update & Repair

One button that brings a Normie Linux machine fully up to date and fixes missing pieces.
Status: **version 0.** It exists and its logic is tested with simulated hardware, but it has
not yet run on a real installed system or a real NVIDIA card. See "Not yet verified" below.

## What the button does

| # | Step | How |
|---|---|---|
| 1 | Check the internet connection | `curl` to fedoraproject.org; stops cleanly if offline |
| 2 | Set up software sources | Adds RPM Fusion free and nonfree using RPM Fusion's official release packages |
| 3 | Add missing compatibility libraries | Downloads `dist/normie-deps.list` from GitHub (names only) and installs what is missing |
| 4 | Update the system | `dnf upgrade --refresh -y` |
| 5 | Update apps | `flatpak update` |
| 6 | Graphics drivers | `normie-gpu apply` (see below) |
| 7 | Finish | Asks for a restart if a new Linux kernel was installed |

Pressing it asks for the administrator password once (polkit). It is also in the application
menu and on the desktop. Where things live:

| Path (in the repo, under `root/`) | What |
|---|---|
| `usr/libexec/normie/normie-update` | The backend script (bash) |
| `usr/libexec/normie/normie-gpu` | NVIDIA detection and driver management (Python) |
| `usr/libexec/normie/normie-update-gui` | The window (PyQt6). Thin: it only displays what the backend reports |
| `usr/share/applications/normie-update.desktop` | Menu entry (a copy sits in `etc/skel/Desktop/` for the desktop icon) |
| `usr/share/polkit-1/actions/org.normielinux.update.policy` | The password prompt |
| `etc/xdg/autostart/normie-first-run.desktop` | At login, offers the NVIDIA driver if a card needs it |
| `etc/normie/update.conf` | Settings, including the GitHub list address |

## "Pull changes from GitHub": how, and what it deliberately does not do

`dist/normie-deps.list` in this repository is a plain list of package names, generated from
the XML by `tools/export-deps.py`. When `DEPS_LIST_URL` in `update.conf` points at its raw
GitHub address, the button installs anything on the list that is missing. So **adding a
dependency to the repo reaches every machine the next time its owner presses the button**,
with no new ISO.

It does **not** download and run scripts from GitHub. A root-level script fetched from a
website is a remote-control channel: if the GitHub account or the connection were ever
compromised, every user's computer would be compromised with it. Instead:

- Only **names** are read. Each must start with a letter or digit (so it can never act as a
  command option) and contain only name characters; anything else is ignored. HTTPS only.
  The tests include malicious lists (`--installroot=...`, shell fragments) to prove this.
- Names install from the repositories already configured, never from an address in the file.
- Updates to the tools themselves (the scripts) are planned to ship as an RPM from our own
  signed repository (Milestone 3), not from raw GitHub.

Set the address once the repository exists, in `root/etc/normie/update.conf`.

## NVIDIA

Drivers come from RPM Fusion's nonfree repository (not bundled in the ISO, which also avoids
redistribution questions). `normie-gpu` reads the card's chip name and picks:

| Card generation | Examples | Driver |
|---|---|---|
| Turing and newer | RTX 20/30/40/50, GTX 16 | current: `akmod-nvidia` |
| Maxwell, Pascal, Volta | GTX 750 to 10-series, GTX 900, Titan V | legacy: `akmod-nvidia-580xx` |
| Fermi, Kepler and older | GTX 400/500, 600/700 | **nothing**: stays on the open-source nouveau driver. The old proprietary drivers are Xorg-only and Fedora KDE is Wayland-first |
| Unknown | very new or unrecognized | **nothing**, unless the PCI id is 0x1E00 or higher (Turing or newer) |

Rules it follows: unknown hardware means do nothing; a driver is only swapped (with
`--allowerasing`) when the installed branch does not match the card; the Secure Boot signing
key is created **before** modules are built so they are signed; if the newest kernel has no
working driver yet, the previous kernel stays the default.

Secure Boot cannot be fully silent. The window shows a one-time password; after the restart
a blue screen asks the user to "Enroll MOK" and type it.

Packages installed (current branch): `akmod-nvidia xorg-x11-drv-nvidia
xorg-x11-drv-nvidia-libs.i686 xorg-x11-drv-nvidia-cuda libva-nvidia-driver(.i686)`. The
legacy branch uses the `-580xx` variants.

## Trying it

**In your VM (safe):** boot the Normie-Live ISO, open "Update & Repair". In the live session
it runs in demo mode (`--dry-run`): you see the whole flow and nothing changes.

**On a real machine with an NVIDIA card, read-only** (changes nothing; run from the repo root):

```
python3 root/usr/libexec/normie/normie-gpu detect
python3 root/usr/libexec/normie/normie-gpu plan
sudo python3 root/usr/libexec/normie/normie-gpu apply --dry-run     # prints the commands only
```

**The automated tests** (simulated GPUs and fake system commands; touch nothing real):

```
python3 -m unittest discover -s tests -v
```

## Not yet verified (be honest with yourself before relying on it)

- Never run on a real NVIDIA card, a real Secure Boot enrollment, or the real `pkexec` prompt.
- The window (`normie-update-gui`) has not been run at all: there was no Qt in the environment it was written in.
- `dnf install --skip-unavailable`, `grubby --set-default` and the `mokutil --generate-hash` /
  `--hash-file` flow are used as documented but unconfirmed on Fedora 45.
- Driver package names and branches come from published Fedora 45 guides and RPM Fusion's howto.

## Not built yet

Btrfs snapshot before updating and automatic rollback; offline (reboot-time) updates; firmware
updates; fixing the Visual C++ problem from `APP-DEPENDENCIES.md`; Fedora 45 to 46 upgrades;
NVIDIA Optimus laptops (a second, integrated GPU); NVIDIA setup without an internet connection;
updates to the tools themselves (Milestone 3).
