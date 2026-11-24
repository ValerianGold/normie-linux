# Publishing on GitHub

What you may publish **now**: this source repository. What waits: ISO files (Fedora branding must be
replaced first, `REBRANDING.md`).

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

## Make the alpha release (source only)

Do this once the first push is done and the **tests workflow is green** on GitHub.

1. Check the two addresses were set (both lines must show your username, not an empty value or `TODO`):

   ```
   cd ~/normie-linux
   grep '^DEPS_LIST_URL=' root/etc/normie/update.conf
   grep '<contact>' Normie-Linux.kiwi
   ```

2. Tag it and create the release. `--prerelease` marks it as an alpha on GitHub:

   ```
   git tag -a v0.1.0-alpha -m "Normie Linux 0.1.0 alpha (source only)"
   git push origin v0.1.0-alpha
   gh release create v0.1.0-alpha --prerelease --title "Normie Linux 0.1.0 alpha (source only)" --notes-file docs/ALPHA-NOTES.md
   ```

3. **Do not attach an ISO.** GitHub adds the source code archives to the release by itself; that is the whole
   release. An ISO waits for the rebrand (see "ISO files" below).

4. Optional polish on the repository page: set the About text to "A beginner-friendly Linux distribution
   based on Fedora (alpha, source only)", add topics such as `linux-distribution`, `fedora`, `kde-plasma`,
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
Only after the rebrand (`REBRANDING.md`, stage R5).

## What must never be committed

Passwords, API keys, SSH keys, signing keys (including any key you later create for a package
repository). The test suite scans for common patterns, but it cannot catch everything.
