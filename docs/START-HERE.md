# Start here

Everything you need to build lives in this repository. Commands below assume
you are in the repo root (`~/normie-linux`) on your **Fedora 45 build machine**,
which already has KIWI (`kiwi-cli`) installed.

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
- Output goes to `~/normie-linux-out/Normie-Live-build/`.
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

## Applying a patch from Claude

Yes: download the `.patch` file, then run the command given with it, from the repo folder.
Patches apply in numeric order (0001, 0002, 0003...), each on top of the previous one.

```
cd ~/normie-linux
git am ~/Downloads/<patch-file-name>.patch
```

`git am` adds the change as a normal commit. If it complains, run `git am --abort` and tell
me the message; nothing is lost. To see what is applied: `git log --oneline`.

## Run the tests

```
python3 -m unittest discover -s tests -v
```

Simulated hardware and fake commands only; it changes nothing on your machine.
