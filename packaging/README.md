# packaging/: Normie Linux's own packages

Four small RPM packages that replace what Fedora's branding packages provide. They are built on the build
host by `tools/build-rpms.sh` into a local repository that the image build reads (see `docs/REBRANDING.md`
and decision D-17).

| Folder | Package | Replaces |
|---|---|---|
| `normie-release/` | `normie-release` | `fedora-release-kde`, `fedora-release-common`, `fedora-release-identity-kde-desktop` |
| `normie-logos/` | `normie-logos` | `fedora-logos` |
| `normie-backgrounds-kde/` | `normie-backgrounds-kde` | `f45-backgrounds-*`, `desktop-backgrounds-kde` |
| `normie-lookandfeel/` | `normie-lookandfeel` | `plasma-lookandfeel-fedora` |

Each folder holds the spec file and its sources. Binary packages only (no source RPMs yet).

- **The artwork** under `*/files/` is generated from `branding/normie-logo.svg` by `make-assets.py` and committed.
  Run it only after changing the logo (needs Pillow and `rsvg-convert`).
- **Changing a package:** edit it, then `tools/build-rpms.sh` (or just run `tools/update-iso.sh`). The build
  notices changes by itself.
- **Tests without rpmbuild:** `tests/test_packaging.py` runs each spec's `%install` section in a scratch
  folder and compares the result with `%files`. So keep specs to plain shell and these macros:
  `%{buildroot}`, `%{_sourcedir}`, `%{_prefix}`, `%{_datadir}`, `%{_sysconfdir}`, `%{_rpmconfigdir}`, `%{version}`,
  `%{release}`, `%{dist}`, and `%global`. The test fails loudly if a spec uses another macro.
- **Version bumps:** when Fedora moves to 46, change `Version:` in `normie-release.spec` (and the version in
  `normie-release/macros.dist`); a test checks it against `<release-version>` in `Normie-Linux.kiwi`.
