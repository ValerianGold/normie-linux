# Rolling out fixes to installed systems

Goal: when someone's app will not run, fix it for everyone **without anyone reinstalling**.
There are three lanes. Which one a fix uses decides how fast it arrives.

| Lane | What changes | How it reaches installed systems | Reinstall needed? |
|---|---|---|---|
| 1. Dependencies | A missing library or package | You edit the package list on GitHub. Machines pick it up through Update & Repair | **No** (once `DEPS_LIST_URL` is set) |
| 2. Fedora, RPM Fusion, Flathub, NVIDIA | Upstream updates and bug fixes | Update & Repair, straight from those projects | No |
| 3. Our own tools and branding | The scripts, window, settings, icons | Our own package repository (ROADMAP M3, `PACKAGE-REPOSITORY.md`). Branding packages: yes, on systems installed from a build that has the repository file. The tools themselves: not packaged yet | Branding: no, once set up. Tools: **yes, today** |

## Worked example (lane 1)

A user reports that "SomeGame" will not start. The issue form asks for the error text.

1. **Find the cause.** For a missing library the error names a file, such as `libfoo.so.1`. On any Fedora machine:
   ```
   dnf provides '*/libfoo.so.1'
   ```
   That shows the package that supplies it, say `foo-libs`. (For 32-bit games add `.i686`.)
2. **Check it is safe.** Read `docs/DEPENDENCY-POLICY.md`. If it only adds a library beside others, it is safe.
3. **Add it** to the matching group in `components/normie/deps-universal.xml`, then:
   ```
   cd ~/normie-linux
   python3 tools/export-deps.py            # regenerates dist/normie-deps.list
   python3 -m unittest discover -s tests   # checks the list is current and well-formed
   python3 tools/check-packages.py         # the new name exists on Fedora (needs a Fedora machine)
   sudo python3 tools/solve-check.py       # and does not conflict with anything
   git add -A && git commit -m "Add foo-libs (fixes SomeGame)" && git push
   ```
4. **It reaches users.** Within a day, each installed system that has already used Update & Repair once
   shows **"Compatibility fixes are available"** with an **Update now** button. Pressing it installs the
   package. (GitHub's cache can delay a push by a few minutes.)

Nobody has to open a terminal, and nothing is reinstalled.

## How the notification works

- `normie-remind` runs once a day per user. If `DEPS_LIST_URL` is set it downloads the list (package
  **names** only, under 1 MB) and compares its fingerprint with the version Update & Repair last applied
  (`/var/lib/normie/deps-applied`). A different fingerprint means a fix is waiting.
- It announces each new version **once**, and never before Update & Repair has applied a list at least once.
- It changes nothing itself. Only the button installs, and only names that pass the strict filter in
  `root/usr/libexec/normie/normie-lib.sh`.
- Privacy: this is one small HTTPS request a day to GitHub, which can see the machine's IP address as it
  can for any visitor. Nothing else is sent. Remove `DEPS_LIST_URL` from `update.conf` to turn it off.

## Why not make scripts update the same way

A script downloaded and run with administrator rights is a remote-control channel: if the GitHub account
were ever compromised, every user's computer would be. Package **names** limit the damage to "installs
extra software from Fedora's own repositories". So lane 3 waits for signed packages (M3).

## Optional second button?

Not needed yet. The preference so far is "too many beats missing", so everything goes in the one list.
An optional "extra packs" window would make sense for something large or risky (for example older Java
from a separate repository, D-10). It can be added later without changing the design above.

## Before the first ISO leaves your hands

1. Run `tools/set-github-user.sh YOUR-USERNAME` so installed systems know where to fetch the list.
2. Remember lane 3: until M3, a bug in the tools themselves means a new ISO.
