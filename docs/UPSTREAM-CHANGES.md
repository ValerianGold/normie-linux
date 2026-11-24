# Changes relative to Fedora's descriptions

Base: https://forge.fedoraproject.org/releng/fedora-kiwi-descriptions (branch `f45`)
Base commit: `daf359394913068f4fc18a8b7aafc404caeb8257` (2026-09-18, "Add graphics_provider.json to FEX-RootFS")

## Modified Fedora files

| File | Change | Why |
|---|---|---|
| `config.sh` | Added a block near the top that appends `KDE-Desktop-Live,KDE-Desktop` to `$kiwi_profiles` when the profile name contains `Normie` | `config.sh` picks the live session (KDE) and graphical boot target by matching substrings of profile names. Without this a Normie ISO could boot to a text console. Remove it once we have confirmed KIWI expands required profiles into that variable (see docs/START-HERE.md step 1) |
| `scripts/fedora-live-iso-label-generator` | Added a block that gives `Normie-*` profiles short ISO labels | Without it the label repeats "Normie" and approaches the 32-character limit |
| `README.md` | Moved to `docs/UPSTREAM-FEDORA-README.md`; new project README at the same path | Project identity |
| `docs/UPSTREAM-FEDORA-README.md` | One link fixed: `VARIANTS.md` is now `../VARIANTS.md` | The file moved one folder down, so its link broke |
| `.gitignore` | Appended build-output patterns | Keep ISOs and logs out of git |

## Added files

`Normie-Linux.kiwi`, `components/normie/`, `repositories/rpmfusion.xml`,
`tools/`, `docs/` (except the moved upstream README), `NOTICE.md`.

## Keeping up with Fedora

The repo's git history includes Fedora's, with the remote named `upstream`:

```
git fetch upstream
git merge upstream/f46      # when Fedora 46's branch is the target
```

Expect small conflicts only in the files listed above. After a merge, run
`python3 tools/validate-kiwi.py`, then `python3 tools/check-packages.py`:
the package names in `deps.xml` can change between Fedora releases.
