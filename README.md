<p align="center"><img src="branding/normie-logo.svg" width="160" alt="Normie Linux logo: a white letter N wrapped in flames"></p>

# Normie Linux

A beginner-friendly Linux distribution, based on Fedora, built so that ordinary
users never have to open a terminal.

> **Status: alpha.** The system builds, boots, installs, updates itself and sets up NVIDIA
> graphics drivers (tested on one real machine so far). **The ISO is on the
> [release page](https://github.com/ValerianGold/normie-linux/releases)**, hosted on SourceForge and the
> Internet Archive because it is too big for GitHub; check the SHA-256 checksum after downloading. No snapshots or
> rollback yet, and installs from the first, 0.1.0, files cannot receive updates ([docs/ROADMAP.md](docs/ROADMAP.md)). Not for anything important.
>
> What works, what is untested and what is missing: [docs/ALPHA-NOTES.md](docs/ALPHA-NOTES.md).

## Goals

- **No terminal, ever.** Every common task has a graphical path, including fixing things that break.
- **One "Update & Repair" button.** Runs a full system upgrade with no questions asked, keeps common dependencies installed and current, and rolls back automatically if something goes wrong.
- **Runs the software people actually use**, including older programs and 32-bit applications, and Windows programs through Wine.
- **Dependency-complete.** We would rather ship a few libraries too many than make a user hunt for a missing one. Size optimization matters, but completeness wins.
- **Graphics drivers handled automatically**, including NVIDIA, as part of first setup.
- **Fedora underneath.** Updates come from Fedora's repositories (plus RPM Fusion and our own), but this is an independent project.

## Not affiliated with Fedora

Normie Linux is an independent project. It is not endorsed by or affiliated with
the Fedora Project or Red Hat. See [NOTICE.md](NOTICE.md).

## Building

Start with [docs/START-HERE.md](docs/START-HERE.md). In short, on a Fedora 45 machine
with KIWI installed:

```
python3 tools/validate-kiwi.py      # fast structural check, no root needed
tools/build.sh                      # builds the Normie-Live ISO (Milestone 1)
```

## Repository layout

| Path | What it is |
|---|---|
| `Normie-Linux.kiwi` | The Normie Linux image description. Start reading here. |
| `components/normie/` | Our own KIWI files: `profiles.xml` (what can be built) and `deps.xml` (dependency set). |
| `repositories/rpmfusion.xml`, `normie-local.xml` | RPM Fusion and our own build-time package repository (ours). `core.xml` is Fedora's. |
| `root/` | Files copied into the ISO as-is (only build-time files now: the boot-partition fix and the build record). |
| `packaging/normie-tools/` | The Update & Repair tools as a package (`files/usr/libexec/normie/`), so fixes reach installed systems. |
| `packaging/` | Our own packages: release files, logos, wallpaper, Plasma look. They replace Fedora's branding packages. |
| `tools/` | `build.sh`, `build-rpms.sh`, `bump-package.sh`, `validate-kiwi.py`, `check-packages.py`, `solve-check.py`, `export-deps.py`, `audit-branding.py`, `try-iso.sh`. |
| `dist/` | `normie-deps.list`: the dependency list the Update & Repair button fetches from GitHub. |
| `tests/` | Automated tests (simulated GPUs, fake commands). |
| `docs/` | Start-here guide, roadmap, design decisions, how fixes roll out, rebranding plan, publishing steps. |
| `.github/` | Automated checks and the issue forms ("an app will not run", bug report). |
| everything else | Fedora's KIWI descriptions, kept unmodified where possible so upstream updates merge cleanly. See [docs/UPSTREAM-CHANGES.md](docs/UPSTREAM-CHANGES.md). |

## License

GPL-3.0-or-later, inherited from the Fedora KIWI descriptions this project builds on. See `COPYING`.
