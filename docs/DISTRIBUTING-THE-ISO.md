# Getting the ISO to people

The rebrand has been checked on a built image (the audit shows no `FAIL`, and a VM install was tried), so the
alpha ISO can be published. This page says where and how.

## Why not GitHub

GitHub keeps your **source** (the recipe) and its release page, but a single release file may be at most about
2 GB, and the full ISO is larger. So the ISO lives somewhere else, and the GitHub release page and README just
link to it.

## Where to put the ISO

| Option | Cost | Good for | Catch |
|---|---|---|---|
| **SourceForge** (project file area) | free | Linux distributions have always used it; fast mirrors; no size limit that matters | Needs an account and a project page; its download page has adverts |
| **Internet Archive** (archive.org) | free | Permanent; makes a torrent automatically | Slower; you give it a collection and a good description |
| **BitTorrent**, with a web seed | free | Takes the load off any single server | Windows users are less used to it; needs a seed that stays online |
| **Your own storage bucket** (Cloudflare R2, Backblaze B2, or a small server) | cents per month | Full control, a clean URL | You pay for traffic (R2 has no download fee); you run it |
| **University and club mirrors** | free | What big distributions do | Only once the project is known; you ask them |

A sensible start: put the ISO on **SourceForge or the Internet Archive**, add a **torrent** later, and keep one
copy of the ISO and its checksum yourself. Many people use two places so one going away is not a problem.

## What to publish next to the ISO

1. **The SHA-256 checksum.** `tools/build.sh` prints it and saves `<iso>.sha256`. People compare it with
   what they downloaded: on Windows `Get-FileHash .\Normie-Linux-....iso` in PowerShell, on Linux `sha256sum`.
2. **A signature**, once you can: `gpg --detach-sign --armor <iso>.sha256`, and publish your public key on
   the project page. Without a signature a checksum only proves the download is intact; with one it proves it is yours.
3. **The package list** the ISO contains, so anyone can see what is inside: `rpm -qa | sort` from a booted
   copy, or the packages named in `Normie-Linux.kiwi`. It also matters for the licences (below).
4. **How to put it on a USB stick** for Windows users: Fedora Media Writer, balenaEtcher or Ventoy all work.
   Say plainly to try it in the live session first, because nothing is installed until they choose to.
5. The **alpha warnings** from `ALPHA-NOTES.md`, on the same page as the download link.

## Before the first public download

- The rebrand is checked: `python3 tools/audit-branding.py` shows no `FAIL` and you have read every `REVIEW`
  line, and you have booted the ISO and looked at the boot menu, login screen, installer and desktop.
- Optional but wise: Fedora's legal list has seen the result (stage R4, `legal@lists.fedoraproject.org`). It is not a
  requirement; see `REBRANDING.md` for what is and is not open.
- **Licences.** The ISO contains GPL software, so people who receive it must be able to get the matching
  source. Fedora publishes the source of its packages; keep the exact package list (item 3) and the commit the
  ISO was built from (`BUILD-INFO.txt` next to the ISO), and say in the release notes where the source comes from.
  The current Full profile uses RPM Fusion's **free** repository only (non-free is commented out in
  `repositories/rpmfusion.xml`). If you ever turn non-free on, check each package's licence before putting it
  in a public ISO. Not legal advice: the legal list is the place to ask.
- **Patents (a separate question from Fedora's trademarks).** The Full ISO currently contains about 15 packages
  from RPM Fusion Free: video and audio codecs such as x264, x265, libde265, vvenc, aptX and the "freeworld"
  GStreamer, FFmpeg and VA-API pieces. Their licences are free, but Fedora does not ship them because of
  software patents (H.264, HEVC and similar), and removing Fedora's name does not change that. Whether it matters
  depends on where you publish from and who downloads; patent pools in practice pursue commercial distributors,
  and some other Fedora-based distributions do ship these. It is still your decision to make on purpose.
  The safe route is an ISO **without** them, with Update & Repair offering to install them afterwards from
  RPM Fusion onto the user's own computer, so you never distribute them. `tools/audit-branding.py` lists
  them. Not legal advice.
- A **fresh VM install** works from the very ISO you upload, not just a previous build.

## Step by step

Replace `SFUSER` with your SourceForge username and `SFPROJECT` with the project's unix name (`normie-linux`
if that was free). Everything is typed in a terminal on the computer that built the ISO.

1. **Build and check.** `tools/update-iso.sh ...`, then `cd ~/normie-linux && python3 tools/audit-branding.py`
   (no `FAIL`, every remaining `REVIEW` line read), then install the ISO in a VM and boot the installed system.
2. **Make the release folder** with the ISO under its public name, a new checksum, the package list and the
   build record:

   ```
   B=~/normie-linux-out/Normie-Full-Live-build
   R=~/normie-linux-out/release-0.1.0-alpha
   mkdir -p "$R" && cd "$R"
   cp --reflink=auto "$(ls $B/*.iso | head -n1)" Normie-Linux-0.1.0-alpha-x86_64.iso
   sha256sum Normie-Linux-0.1.0-alpha-x86_64.iso > Normie-Linux-0.1.0-alpha-x86_64.iso.sha256
   cp "$B/BUILD-INFO.txt" .
   rpm --root "$B/build/image-root" -qa | sort > Normie-Linux-0.1.0-alpha-packages.txt
   cat *.sha256; wc -l Normie-Linux-0.1.0-alpha-packages.txt
   ```

   Keep this folder: it is exactly what you upload.
3. **Check the copy** matches before uploading: `cd "$R" && sha256sum -c *.sha256`. The checksum must be the
   same as the one `update-iso.sh` printed for the original file.
4. **SourceForge (the ISO):** create a free account, then a project (Project Admin, unix name e.g. `normie-linux`;
   in its tool list, tick only **Files**). Upload with rsync, which can resume a broken transfer (add your
   SSH key first, under Account Settings, SSH Settings; SourceForge recommends rsync above 100 MB):

   ```
   cd "$R"
   rsync -avP -e ssh Normie-Linux-0.1.0-alpha-x86_64.iso Normie-Linux-0.1.0-alpha-x86_64.iso.sha256 BUILD-INFO.txt Normie-Linux-0.1.0-alpha-packages.txt SFUSER@frs.sourceforge.net:/home/frs/project/SFPROJECT/0.1.0-alpha/
   ```

   If SourceForge's own rsync page shows a different path, use that one. In the project's Files tab set the ISO as the
   default download, and add a `README` in the folder with the checksum and the alpha warning.
5. **Internet Archive (second copy):** make a free account, use the Upload button, give the item a title, an
   identifier made only of letters, numbers, dashes and underscores (such as `normie-linux-0-1-0-alpha`; periods are
   not allowed), a description that begins with the alpha warning, and the same four files. File names must be plain
   ASCII (no accents or spaces). The Archive makes a torrent for most items; the item page shows whether it did.
6. **Tag the commit the ISO was built from** (it is named in `BUILD-INFO.txt`; use that commit, not the newest one,
   so the published source matches the published ISO), then create the release without the ISO. Put the download
   links in the notes:

   ```
   cd ~/normie-linux
   git tag -a v0.1.0-alpha COMMIT -m "Normie Linux 0.1.0 alpha"
   git push origin v0.1.0-alpha
   SUM=$(cut -d' ' -f1 "$R"/Normie-Linux-0.1.0-alpha-x86_64.iso.sha256)
   { printf '## Download the ISO (about 5 GB)\n\n- SourceForge: https://sourceforge.net/projects/SFPROJECT/files/0.1.0-alpha/\n- Internet Archive: https://archive.org/details/normie-linux-0-1-0-alpha\n\nSHA-256 of `Normie-Linux-0.1.0-alpha-x86_64.iso`:\n\n`%s`\n\n' "$SUM"; cat docs/ALPHA-NOTES.md; } > "$R/release-notes.md"
   gh release create v0.1.0-alpha --prerelease --title "Normie Linux 0.1.0 alpha" --notes-file "$R/release-notes.md" "$R/Normie-Linux-0.1.0-alpha-x86_64.iso.sha256" "$R/Normie-Linux-0.1.0-alpha-packages.txt" "$R/BUILD-INFO.txt"
   ```

   Replace `COMMIT` with the commit from `BUILD-INFO.txt`.
7. Do one download from each place, check the checksum, and boot it.

## Rough size and cost

A full ISO is a few GB. One thousand downloads is a few TB of traffic: free on SourceForge or the Internet Archive,
about nothing on Cloudflare R2, and a real bill on most other clouds. That is why the first two come first.
