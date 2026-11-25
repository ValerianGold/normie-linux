# Our own package repository (milestone M3)

**M3 is "milestone 3" in `ROADMAP.md`:** Normie Linux's own repository of packages. Today the four packages that
make Normie Linux look and be itself (`normie-release`, `normie-logos`, `normie-backgrounds-kde`,
`normie-lookandfeel`) only reach a computer by installing from the ISO. With a repository, Update & Repair
installs a changed logo, wallpaper or release file on every installed system, like any other update.

We use **Copr**, a free build service run by the Fedora project. You upload source packages; Copr builds them
for Fedora 45, **signs** them with a key of its own, and serves them as a repository. You never hold a signing key.

## How it fits together

1. `tools/build-srpms.sh` makes one **source package** (`.src.rpm`) per folder under `packaging/`.
2. `tools/publish-packages.sh` sends them to your Copr project (`copr-cli build`).
3. Copr builds and signs them. The repository is at
   `https://download.copr.fedorainfracloud.org/results/YOU/normie-linux/`.
4. `normie-release` installs `/etc/yum.repos.d/normie.repo`, which points at that address. From then on
   `dnf upgrade` (which Update & Repair runs) sees new versions.

**A package only reaches installed systems if its `Version` or `Release` number goes up.** Change the logo,
raise `Release:` by one in `packaging/normie-logos/normie-logos.spec`, add a line to `%changelog`, publish. If
you forget, Copr builds it but nothing updates, because dnf thinks it already has that version.

## What installed systems get

- **Systems installed from an ISO built after this change** have the repository from the start.
- **Systems installed from the 0.1.0 alpha ISO** have no `normie.repo`, so they cannot see it. They need either
  a reinstall or, for a technical tester, one command: `sudo dnf copr enable YOU/normie-linux` (needs the dnf
  Copr plugin, which the 0.1.0 ISO may not include).

So the next ISO (0.1.1 alpha) should be built after the repository is set up.

## Step by step (you do the accounts, the scripts do the rest)

1. **Make a Copr login.** Go to <https://copr.fedorainfracloud.org> and use Log in. Copr signs you in with a free
   Fedora Account (make one when it asks; the sign-in page lists what it accepts).
2. **Create the project.** Click New Project:
   - Name: `normie-linux`
   - Chroots (the systems to build for): tick **`fedora-45-x86_64`**. If Fedora 45 is not listed, tell me what it lists.
   - Description: "Normie Linux's own packages: release files, logo, wallpaper and Plasma look."
   - Leave "Enable internet access during builds" off. Save.
3. **Get your API token** (lets the script upload as you). Open <https://copr.fedorainfracloud.org/api/>, copy the whole
   block under "Copy this to ~/.config/copr", and then in a terminal:

   ```
   mkdir -p ~/.config && nano ~/.config/copr
   chmod 600 ~/.config/copr
   ```

   Paste, save (Ctrl+O, Enter, Ctrl+X). The token is a password: never paste it into an issue, chat or commit.
4. **Install the two tools** (once): `sudo dnf install copr-cli rpm-build`
5. **Tell the project your Copr name** (the name at the top right of Copr; replace `YOURCOPRNAME`):

   ```
   cd ~/normie-linux
   tools/set-copr-user.sh YOURCOPRNAME
   python3 -m unittest discover -s tests
   git add -A && git commit -m "Set the Copr repository address" && git push
   ```

6. **Publish:** `cd ~/normie-linux && tools/publish-packages.sh`. It builds the source packages and sends the four to
   Copr, one after the other. Watch <https://copr.fedorainfracloud.org/coprs/YOURCOPRNAME/normie-linux/builds/>
   until all four show **succeeded**.
7. **Check the repository exists:** open
   `https://download.copr.fedorainfracloud.org/results/YOURCOPRNAME/normie-linux/pubkey.gpg` in a browser.
   A block of text starting `-----BEGIN PGP PUBLIC KEY BLOCK-----` means the packages are signed and served.

## Changing something later (the logo, for example)

1. Replace `branding/normie-logo.svg`, then `python3 packaging/make-assets.py` (needs Pillow and rsvg-convert).
2. In each affected spec raise `Release:` (for example `1%{?dist}` to `2%{?dist}`) and add a `%changelog` line.
   The changelog date must be a real date.
3. `python3 -m unittest discover -s tests`, commit, push, then `tools/publish-packages.sh`.
4. On an installed system, **Update & Repair** installs the new version. A few things only show after a restart
   (the boot splash, the login screen).

Also rebuild the ISO (`tools/update-iso.sh`) when you want new installs to carry it.

## Honest limits

- Copr is run by the Fedora project and has its own terms. If it ever stopped serving you, the repository address
  lives in `normie-release`, so moving to your own server is one package update, as long as the old address still works
  for that last update. Plan for a second home before there are many users.
- Nothing here updates the **tools** (Update & Repair itself, `root/`). They are not packaged yet; that is the next
  step (`normie-tools`). Until then a tool fix needs a new ISO.
- The dependency list still arrives from GitHub (`ROLLING-OUT-FIXES.md`, lane 1); that is separate and keeps working.
