# Normie Linux

A beginner-friendly Linux distribution, based on Fedora, built so that ordinary
users never have to open a terminal.

> **Status: early development.** The project currently builds a Fedora 45 KDE
> live ISO under the Normie name (Milestone 1). The features below are the
> goals; see [docs/ROADMAP.md](docs/ROADMAP.md) for what exists today.

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
| `repositories/rpmfusion.xml` | RPM Fusion repositories (ours). `core.xml` is Fedora's. |
| `root/` | Files copied into the ISO as-is, including the Update & Repair tools (`root/usr/libexec/normie/`). |
| `tools/` | `build.sh`, `validate-kiwi.py`, `check-packages.py`, `solve-check.py`, `export-deps.py`. |
| `dist/` | `normie-deps.list`: the dependency list the Update & Repair button fetches from GitHub. |
| `tests/` | Automated tests (simulated GPUs, fake commands). |
| `docs/` | Start-here guide, roadmap, design decisions, list of changes to Fedora's files. |
| everything else | Fedora's KIWI descriptions, kept unmodified where possible so upstream updates merge cleanly. See [docs/UPSTREAM-CHANGES.md](docs/UPSTREAM-CHANGES.md). |

## License

GPL-3.0-or-later, inherited from the Fedora KIWI descriptions this project builds on. See `COPYING`.
