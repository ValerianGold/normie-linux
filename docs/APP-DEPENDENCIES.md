# App dependency register

Normie Linux's core promise: if a user downloads a popular app, its dependencies are already
there. This file records, per app, **what it needs, where that came from, and what we did about it**,
so entries can be re-checked when an app changes. Add a section for each app we support.

Policy: ship dependencies, not apps (see DECISIONS.md D-4).

## Xodus Nexus

Open-source launcher for Microsoft Store / Game Pass PC games on Linux.
Project: https://github.com/domsvoboda/xodus-nexus (wiki: Getting started, Compatibility patches).
Checked: 2026-11-21. The project is very new and changes quickly, so re-check each Fedora release.

### Source 1: the project's `scripts/install.sh`, Fedora branch (authoritative)

`curl tar xz fuse webkit2gtk4.1 gtk3 nss libXtst alsa-lib desktop-file-utils`

- `fuse`: AppImage support (also `fuse-libs` for `libfuse.so.2`).
- `webkit2gtk4.1`, `gtk3`: the sign-in window.
- `nss`, `libXtst`, `alsa-lib`: Electron runtime libraries.
- The script states a compiler, Rust/Cargo and protoc are **not** needed for the prebuilt backend.

### Source 2: field report, Fedora Workstation 44 (Reddit r/XodusNexus, Nov 2026)

The official AppImage route did not work for the author; these steps did.

| Item | In `deps.xml`? | Notes |
|---|---|---|
| `gcc gcc-c++ make cmake openssl openssl-libs openssl-devel dbus-devel pkgconf-pkg-config` | yes (build tools group) | Not required by the official script. Kept (completeness policy). Unknown which, if any, actually fixed the author's problem. |
| `glibc.i686 gnutls.i686 gnutls.x86_64` | yes | Plausible real fix: the runtime is Wine-based and Wine uses gnutls. |
| `fuse fuse-libs` | yes | Matches the official script. |
| `msitools unzip curl` | added | Tools for the Visual C++ repair workaround below. |
| Google Chrome | **no** | Not in Fedora repos. See DECISIONS.md D-9. |
| Full system upgrade + reboot first | n/a | Handled by Update & Repair (D-6). |

### Known app-level problem with a manual workaround (not a package)

Installing "VC++" from inside the app can fail with exit code 130. The field report fixes it by
extracting the Visual C++ runtime DLLs with `dark.exe` (WiX 3.11 binaries, a download, not a Fedora
package) and `msiextract`, copying them into the game's Wine prefix, and setting DLL overrides.
This is a candidate for a future automated "fix" module in Update & Repair. It is **not** implemented,
and it should be re-verified first: the runtime name and prefix path in the report are version-specific.
