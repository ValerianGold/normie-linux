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

Set these once per release (the example is the 0.1.2 alpha). `SFUSER` is your SourceForge username and
`SFPROJECT` the project's unix name (`normie-linux`). Everything is typed in a terminal on the computer that
built the ISO, and the same terminal window must be used for all the steps, because they share these names:

```
VER=0.1.2-alpha
SFUSER=your-sourceforge-username
SFPROJECT=normie-linux
IAID=normie-linux-${VER//./-}            # Internet Archive names allow no periods
NAME=Normie-Linux-$VER-x86_64
B=~/normie-linux-out/Normie-Full-Live-build
R=~/normie-linux-out/release-$VER
```

1. **Build and check.** `tools/update-iso.sh ...`, then `cd ~/normie-linux && python3 tools/audit-branding.py`
   (no `FAIL`, every remaining `REVIEW` line read), then install the ISO in a VM, boot the installed system and
   **run Update & Repair: its log must show no `404`** (`START-HERE.md`).
2. **Make the release folder** with the ISO under its public name, a new checksum, the package list and the
   build record:

   ```
   mkdir -p "$R" && cd "$R"
   cp --reflink=auto "$(ls $B/*.iso | head -n1)" $NAME.iso
   sha256sum $NAME.iso > $NAME.iso.sha256
   cp "$B/BUILD-INFO.txt" .
   rpm --root "$B/build/image-root" -qa | sort > $NAME-packages.txt
   cat *.sha256; wc -l $NAME-packages.txt
   ```

   Keep this folder: it is exactly what you upload. The checksum must be the same as the one
   `update-iso.sh` printed for the original file (`cat "$B"/*.sha256`).
3. **SourceForge (the ISO):** create a free account, then a project (Project Admin, unix name e.g. `normie-linux`;
   in its tool list, tick only **Files**). Upload with rsync, which can resume a broken transfer (add your
   SSH key first, under Account Settings, SSH Settings, or just type your password when asked):

   ```
   cd "$R"
   rsync -avP -e ssh $NAME.iso $NAME.iso.sha256 BUILD-INFO.txt $NAME-packages.txt $SFUSER@frs.sourceforge.net:/home/frs/project/$SFPROJECT/$VER/
   ```

   If SourceForge's own rsync page shows a different path, use that one. In the project's Files tab set the ISO as the
   default download (the little (i) beside the file), and add a `README` in the folder with the checksum and the
   alpha warning.
4. **Internet Archive (second copy):** the web uploader works for small files, but a 5 GB file can hang on "finishing
   upload". The command line is dependable. Sign-in with Google has no password, so use the keys from
   <https://archive.org/account/s3.php> in `~/.config/ia.ini`:

   ```
   [s3]
   access = YOUR-ACCESS-KEY
   secret = YOUR-SECRET-KEY
   ```

   Then (the first line downloads the tool once):

   ```
   cd "$R"
   [ -x ./ia ] || { curl -LOs https://archive.org/download/ia-pex/ia && chmod +x ./ia; }
   ./ia --config-file ~/.config/ia.ini upload $IAID $NAME.iso $NAME.iso.sha256 BUILD-INFO.txt $NAME-packages.txt --checksum --retries 10 --metadata="mediatype:software" --metadata="title:Normie Linux $VER (x86_64 live ISO)" --metadata="description:ALPHA, not for anything important. Beginner-friendly Linux based on Fedora. SHA-256: $(cut -d' ' -f1 $NAME.iso.sha256). Source: https://github.com/ValerianGold/normie-linux"
   ```

   The identifier may use only letters, numbers, dashes and underscores. File names must be plain ASCII.
5. **Tag the commit the ISO was built from** (it is named in `BUILD-INFO.txt`; use that commit, not the newest one,
   so the published source matches the published ISO), then create the release without the ISO. Put the download
   links in the notes. Replace `COMMIT` with the commit from `BUILD-INFO.txt`:

   ```
   cd ~/normie-linux
   git tag -a "v$VER" COMMIT -m "Normie Linux $VER"
   git push origin "v$VER"
   SUM=$(cut -d' ' -f1 "$R/$NAME.iso.sha256")
   { printf '## Download the ISO (about 5 GB)\n\n- SourceForge: https://sourceforge.net/projects/%s/files/%s/\n- Internet Archive: https://archive.org/details/%s\n\nSHA-256 of `%s.iso`:\n\n`%s`\n\n' "$SFPROJECT" "$VER" "$IAID" "$NAME" "$SUM"; cat docs/ALPHA-NOTES.md; } > "$R/release-notes.md"
   gh release create "v$VER" --prerelease --title "Normie Linux $VER" --notes-file "$R/release-notes.md" "$R/$NAME.iso.sha256" "$R/$NAME-packages.txt" "$R/BUILD-INFO.txt"
   ```

   Do not attach the ISO itself: GitHub allows about 2 GB per file.
6. Do one download from each place, check the checksum (`sha256sum`), and boot it.

## Replacing a release you withdraw

Only do this for a release that was never announced. Give the replacement a new version number rather than
reusing the old one: a reused name means two different files under one checksum.

```
cd ~/normie-linux
OLD=0.1.1-alpha
gh release delete "v$OLD" --cleanup-tag --yes          # the GitHub release and its tag
git tag -d "v$OLD"                                       # your local copy of the tag
sftp $SFUSER@frs.sourceforge.net                         # then, at the sftp> prompt, one line each:
#   cd /home/frs/project/$SFPROJECT
#   rm $OLD/Normie-Linux-$OLD-x86_64.iso   (and the same for .iso.sha256, BUILD-INFO.txt and -packages.txt)
#   rmdir $OLD
#   bye
cd ~/normie-linux-out/release-$OLD
./ia --config-file ~/.config/ia.ini delete normie-linux-${OLD//./-} --all
./ia --config-file ~/.config/ia.ini metadata normie-linux-${OLD//./-} --modify="title:WITHDRAWN - Normie Linux $OLD (replaced)" --modify='description:<b>Withdrawn:</b> replaced. Please use the new release: <a href="https://archive.org/details/'"$IAID"'">Normie Linux '"$VER"'</a>'
```

The Internet Archive keeps a copy of deleted files in the item's history, and the item page itself stays
(an empty page that says it was withdrawn). Item pages cannot be fully removed by their owner.

## Rough size and cost

A full ISO is a few GB. One thousand downloads is a few TB of traffic: free on SourceForge or the Internet Archive,
about nothing on Cloudflare R2, and a real bill on most other clouds. That is why the first two come first.
