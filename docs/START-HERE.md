# Start here

Everything you need to build lives in this repository. Commands below assume
you are in the repo root (`~/normie-linux`) on your **Fedora 45 build machine**,
which already has KIWI (`kiwi-cli`) installed.

## One-time setup for the Normie packages

The image contains our own release files, logos, wallpaper and Plasma look (`packaging/`). Building them
needs two tools, installed once:

```
sudo dnf install rpm-build createrepo_c
```

After that `tools/update-iso.sh` and `tools/build.sh` build the packages by themselves when they changed.
To do it by hand: `tools/build-rpms.sh`. After a build, run `python3 tools/audit-branding.py` in a terminal on your own computer (not in the VM); it lists
anything that still mentions Fedora (see `REBRANDING.md`).

## Looking at a new ISO in a virtual machine

```
sudo dnf install qemu-system-x86 edk2-ovmf     # once
tools/try-iso.sh                                # boots the newest ISO; you can try it live or install onto a virtual 40 GB disk
tools/try-iso.sh --installed                    # afterwards: boot what you installed, without the ISO
tools/try-iso.sh --fresh                        # start over with an empty disk
```

Nothing touches your real disks. Things to look at: the boot menu, the login screen, the desktop and wallpaper,
the Start button, the pins (Start menu and taskbar), Settings > About, the installer.

Using virt-manager (Virtual Machine Manager) instead is fine: create a VM from the ISO, tick "Customize
configuration before install", and under Overview set Firmware to **UEFI x86_64** (the one with OVMF in its name),
then give it 6 GB of memory, 4 CPUs and a 40 GB disk. `try-iso.sh` just does the same with QEMU directly.

The audit is separate: run `cd ~/normie-linux && python3 tools/audit-branding.py` in a terminal on your own
computer, not inside the VM. It reads the build output on your disk; the VM does not have it.

## The one thing to remember: a patch changes the recipe, not the ISO

```
patch or edit  -->  the repo (the recipe)  -->  tools/build.sh  -->  a NEW ISO  -->  install it  -->  a running system
                                                (you must run it)                    (reinstall)       (which then updates itself from
                                                                                                        Fedora, Flathub, RPM Fusion and
                                                                                                        the GitHub package list)
```

- `git am` and edits change only the source in `~/normie-linux`. An ISO that is already in
  `~/normie-linux-out/` stays exactly as it was. **Every change needs a new build to reach an ISO.**
- A system you already installed does not receive recipe changes either (that needs our own package
  repository, ROADMAP M3). It receives only Fedora's updates and the dependency list.

**Which ISO do I have?** Every build now records the exact version it was made from:

```
cat ~/normie-linux-out/Normie-Full-Live-build/BUILD-INFO.txt   # next to the ISO (builds from now on)
ls ~/normie-linux-out/isos/                                    # every ISO ever built, named by its commit
cat /usr/share/normie/build-info                               # on a running or live system
```

`tools/build.sh` also keeps the previous ISO in `isos/` and clears the folder before building (kiwi will
not build into a folder that already holds a build). For an ISO made before this existed, compare dates:

```
cd ~/normie-linux
ls -l --time-style=long-iso ~/normie-linux-out/Normie-Full-Live-build/*.iso
git log --date=iso --format='%cd  %h  %s' -8
```

The ISO must be **newer** than the newest commit you want in it. On an installed system,
`ls /usr/libexec/normie/` also tells you: `normie-sources` means patch 0005 or later, `normie-lib.sh` means 0006 or later.

## 0. One-time setup

```
sudo dnf upgrade distribution-gpg-keys     # signing keys for Fedora and RPM Fusion repos
```

If the build later fails with "Couldn't read a file:// file ... RPM-GPG-KEY",
this package is too old. Upgrading it fixes that.

## 1. Check the structure (seconds, no root)

```
python3 tools/validate-kiwi.py
```

Expected: `OK: no structural problems found.`

Optional but useful (does not build anything): see what KIWI hands to `config.sh`.

```
kiwi-ng --type=iso --kiwi-file=Normie-Linux.kiwi --profile=Normie-Live \
  image info --description . --print-kiwi-env | grep -i profiles
```

If the output lists `KDE-Desktop-Live` and `KDE-Desktop` as well as `Normie-Live`,
KIWI expands required profiles and the `config.sh` patch is only a safety net.
If it lists only `Normie-Live`, the patch is essential. Either way it is harmless.
If this command errors out, skip it and tell me the message.

## 2. Milestone 1: build the base ISO

```
tools/build.sh
```

- Builds `Normie-Live`: a Fedora 45 KDE live ISO under the Normie name. It
  should be identical in content to your earlier baseline.
- Output goes to `~/normie-linux-out/Normie-Live-build/` (every ISO is also kept, named by commit, in `~/normie-linux-out/isos/`).
- The full log is saved at `~/normie-linux-out/Normie-Live.log`. **If it fails,
  paste me the last ~60 lines of that file** (the script also prints them).
- It takes a while and needs several GB of free disk space.

Optional: test the ISO in a VM before touching real hardware:

```
qemu-system-x86_64 -enable-kvm -cpu host -m 8G -smp 4 \
  -audiodev pipewire,id=snd0 -device intel-hda -device hda-output,audiodev=snd0 \
  -cdrom ~/normie-linux-out/Normie-Live-build/*.iso -boot d
```

The two `-audiodev`/`-device` lines give the VM a sound card (without them it shows no audio output).
If your QEMU rejects `pipewire`, use `-audiodev pa,id=snd0` instead. For the full ISO, replace
`Normie-Live-build` with `Normie-Full-Live-build`.

## 3. Milestone 2: the full ISO (do NOT skip the preflight)

The full profile adds RPM Fusion and the dependency set from your prototype.
Those ~174 package names have never been checked against real repositories,
and one wrong name fails the entire build.

```
# Enable RPM Fusion on the build host so the checker can see its packages
# (official RPM Fusion procedure; verifies the package signature):
sudo dnf install distribution-gpg-keys
sudo rpmkeys --import /usr/share/distribution-gpg-keys/rpmfusion/RPM-GPG-KEY-rpmfusion-free-fedora-$(rpm -E %fedora)
sudo dnf --setopt=localpkg_gpgcheck=1 install \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm

mkdir -p ~/normie-linux-out
python3 tools/check-packages.py 2>&1 | tee ~/normie-linux-out/preflight.txt
```

Paste me `preflight.txt`. We fix every name it lists. Then check that everything can be installed
**together** (names existing is not enough). Run the control first, to prove the tool works on your machine:

```
sudo python3 tools/solve-check.py Normie-Live        # known-good base: should say OK
sudo python3 tools/solve-check.py                    # the full set
```

Paste me any PROBLEMS output. Only when both are clean:

```
tools/build.sh Normie-Full-Live
```

## Where things are

| I want to... | Look in |
|---|---|
| Add or remove a package from the full ISO | `components/normie/deps.xml` |
| Add a new buildable ISO variant | `components/normie/profiles.xml` |
| Change which repositories are used | `repositories/rpmfusion.xml` (ours), `repositories/core.xml` (Fedora's) |
| Change what runs inside the image at build time | `config.sh` (Fedora's; edits get listed in `docs/UPSTREAM-CHANGES.md`) |
| See build logs | `~/normie-linux-out/<profile>.log` |
| Know what is decided vs open | `docs/DECISIONS.md` |
| Know what to do next | `docs/ROADMAP.md` |

## Applying a patch from Claude and getting a new ISO (the one command)

Download the `.patch` file, then run this, **replacing the number** with the patch you downloaded:

```
~/normie-linux/tools/update-iso.sh ~/Downloads/0010-*.patch
```

It works from any folder. It applies the patch, runs every check, and builds a new ISO, stopping at the
first problem and telling you what to do. A patch that is already applied is skipped, not an error. The
ISO it replaces is kept in `~/normie-linux-out/isos/`, so nothing is ever lost.

| You want | Run |
|---|---|
| Patch, check and rebuild (the usual) | `~/normie-linux/tools/update-iso.sh ~/Downloads/0010-*.patch` |
| Several patches at once | `~/normie-linux/tools/update-iso.sh ~/Downloads/0010-*.patch ~/Downloads/0011-*.patch` |
| Rebuild what is already in the repo | `~/normie-linux/tools/update-iso.sh` |
| Apply and check but do not build yet | `~/normie-linux/tools/update-iso.sh --no-build ~/Downloads/0010-*.patch` |
| Build the smaller base image | `~/normie-linux/tools/update-iso.sh --profile Normie-Live ~/Downloads/0010-*.patch` |

If it stops, send me the message it printed (and `~/normie-linux-out/preflight.txt` if it names that file).
To see what changed in a patch first: `git apply --stat ~/Downloads/0010-*.patch`.

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `previous rebase directory .git/rebase-apply still exists but mbox given` | An earlier patch attempt was left half-finished; git refuses to start another | `tools/update-iso.sh` clears it for you. By hand: `cd ~/normie-linux && git am --abort` |
| `already exists in index` (many files) while applying a patch | That patch is already applied | Nothing is wrong. `tools/update-iso.sh` skips it by itself. By hand: `git am --abort` |
| `KiwiRootDirExists: Root directory ... already exists` | kiwi will not build over an earlier build | `tools/build.sh` (and so `tools/update-iso.sh`) keeps the old ISO and clears the folder first |
| `fatal: not a git repository` | You ran a command outside the project folder | `cd ~/normie-linux` first, or use `~/normie-linux/tools/update-iso.sh`, which works from anywhere |
| A check stops with `STOPPED:` | The script found a real problem and did not build | Send me the message it printed |

## Run the tests

```
python3 -m unittest discover -s tests -v
```

Simulated hardware and fake commands only; it changes nothing on your machine.
