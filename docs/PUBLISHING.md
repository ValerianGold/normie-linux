# Publishing on GitHub

You publish two things: this source repository on GitHub, and the ISO on SourceForge and the Internet Archive
(`DISTRIBUTING-THE-ISO.md`).

## Where to type the commands

Every command on this page is typed in a **terminal opened in the project folder**. Open a terminal and run
`cd ~/normie-linux` first; a command like `tools/set-github-user.sh` only works from there ("No such file or
directory" almost always means the terminal was somewhere else). `pwd` shows where you are.

## One-time setup

1. Create a GitHub account and **turn on two-factor login** (Settings, then Password and authentication).
   This matters more than usual: the dependency list in this repository is delivered to installed systems.
2. Create a new **empty** repository named `normie-linux`: no README, no license, no `.gitignore`.
   Make it **public** (installed systems fetch the list without logging in).
3. On your computer:
   ```
   sudo dnf install gh
   gh auth login        # GitHub.com, HTTPS, yes to "authenticate Git", log in through the browser
   ```

## Publish

```
cd ~/normie-linux
tools/set-github-user.sh YOUR-USERNAME      # sets the update-list address and the project address
python3 -m unittest discover -s tests       # must pass
git add -A
git commit -m "Set GitHub address"
git remote add origin https://github.com/YOUR-USERNAME/normie-linux.git
git push -u origin main
```

Then open `https://raw.githubusercontent.com/YOUR-USERNAME/normie-linux/main/dist/normie-deps.list`
in a browser. You should see the package list. If you do, installed systems will see it too.

## After the first push

- **Actions tab:** the `tests` workflow should turn green. It runs the same tests as above.
- **Settings, then Code security:** turn on **Private vulnerability reporting** (`SECURITY.md` points to it).
- Optional but wise: Settings, then Branches, add a rule for `main` that requires the tests to pass.
- The commits carry a placeholder author name from the first import. That is harmless. Your own commits
  use your Git identity (`git config --global user.name` / `user.email`).

## Make the alpha release

Do this once the first push is done and the **tests workflow shows a green check** on GitHub.

The release is made after the ISO is uploaded, because its notes carry the download links and the checksum.
The exact steps (checksums, SourceForge, Internet Archive, tagging the commit the ISO was built from, creating the
release with `gh release create --prerelease`) are in `DISTRIBUTING-THE-ISO.md`, "Step by step".
**Do not attach an ISO to the release:** GitHub allows about 2 GB per file and the full ISO is larger.
Attach only small files (the checksum, the package list, `BUILD-INFO.txt`).

First check the two addresses were set (both lines must show your username, not an empty value or `TODO`):

```
cd ~/normie-linux
grep '^DEPS_LIST_URL=' packaging/normie-tools/files/etc/normie/update.conf
grep '<contact>' Normie-Linux.kiwi
```

Optional polish on the repository page: set the About text to "A beginner-friendly Linux distribution
based on Fedora (alpha)", add topics such as `linux-distribution`, `fedora`, `kde-plasma`,
`kiwi`, and upload a preview picture made from the logo (Settings, then Social preview):

```
rsvg-convert -w 640 -h 640 branding/normie-logo.svg -o ~/normie-logo-640.png
```

## Routine

```
~/normie-linux/tools/update-iso.sh ~/Downloads/<patch>.patch   # apply, check and rebuild (see START-HERE.md)
cd ~/normie-linux
git push
```

## ISO files

GitHub release files are limited to about 2 GB each and these ISOs are larger. Host ISOs elsewhere
(your own server, a torrent, a file host) and publish the SHA-256 checksum next to the download link.
Where and how: `DISTRIBUTING-THE-ISO.md`.

## What must never be committed

Passwords, API keys, SSH keys, signing keys (including any key you later create for a package
repository). The test suite scans for common patterns, but it cannot catch everything.
