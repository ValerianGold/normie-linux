# Dependency policy: maximum support without conflicts

The goal: a user downloads a popular app and it works. The risk: every package we add can
conflict with something else. These rules keep "ship more" from turning into "ship broken".

## What is safe to add

1. **Libraries that sit beside others.** A new shared library, a compat package with its own soname
   (`compat-openssl11`, `libxcrypt-compat`), a font, a codec plugin. Two versions can be installed at once.
2. **Runtimes designed to coexist.** Java uses the `alternatives` system; .NET installs side by side.
3. **The 32-bit twin of a 64-bit library** (`.i686`) when it exists. Different architecture, different files.
4. **Tools an app's own installer asks for** (read the installer; see `APP-DEPENDENCIES.md`).

## What needs a decision first (do not just add)

| Kind | Example | Why |
|---|---|---|
| **Replacement** of a Fedora package | `ffmpeg` vs `ffmpeg-free`, `mesa-*-freeworld` vs Mesa | Both cannot be installed; one must replace the other, on **every** architecture we ship (D-7) |
| **Needs another repository** | `steam`, `unrar`, NVIDIA (RPM Fusion nonfree), Chrome (Google) | Build fails without the repo; also a licensing question (D-8, D-9) |
| **An app, not a dependency** | Steam, Lutris, browsers | Policy: dependencies only (D-4) |
| **A kernel module** | `akmod-*` | Rebuilds on every kernel update; belongs to the GPU design (D-5) |

## The verification workflow (before every full build)

```
python3 tools/validate-kiwi.py             # structure is sound (seconds)
python3 tools/check-packages.py            # every name exists, 32-bit builds exist
sudo python3 tools/solve-check.py Normie-Live        # control: the known-good base resolves
sudo python3 tools/solve-check.py                    # the full set resolves with no conflicts
tools/build.sh Normie-Full-Live
```

## Adding a package later

1. Decide which table above it falls in. If it needs a decision, write it in `DECISIONS.md` first.
2. Add it to the matching group in `components/normie/deps-universal.xml`. If the group's risk label
   is SAFE, keep it that way.
3. Run the workflow above. If `solve-check.py` reports a conflict, remove the package, do not
   remove the other side of the conflict.
4. For an app, add its evidence to `APP-DEPENDENCIES.md`.

## Deriving an RPM app's dependencies instead of guessing

For an app that is packaged as an RPM, DNF can list exactly what it needs:

```
dnf repoquery --requires --resolve --arch=x86_64,i686,noarch <package-name>
```

Add those dependencies (not the app) to the register. This is the most reliable way to support
apps like Steam without shipping them.
