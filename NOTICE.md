# Notice

## Upstream

Normie Linux builds on the **Fedora KIWI descriptions**
(https://forge.fedoraproject.org/releng/fedora-kiwi-descriptions), licensed
GPL-3.0-or-later (see `COPYING`). `kiwi-build` and the helper scripts under
`scripts/` were written by Neal Gompa and other Fedora contributors. Our
changes to Fedora's files are listed in `docs/UPSTREAM-CHANGES.md`.

## Trademarks

"Fedora" and the Fedora logos are trademarks of Red Hat, Inc. Normie Linux is
not affiliated with or endorsed by the Fedora Project or Red Hat.

Fedora's trademark guidelines do not permit redistributing a modified system
under Fedora's name and branding. **Before publishing any Normie Linux ISO**,
the branding packages inherited from Fedora (`fedora-release*`,
`fedora-logos`, and similar) must be replaced. This is tracked as Milestone 6
in `docs/ROADMAP.md`. Publishing only this source repository is fine now.

## The Normie Linux logo

The logo in `branding/` (a white N with pixel flames on a dark badge) is original artwork made for this
project. It contains no Fedora artwork. It is covered by the same license as the rest of the project.

## Third-party software

Builds that include the NormieFull profile pull packages from RPM Fusion,
including software with licenses that restrict redistribution. Check the
license of each such package before publishing an ISO that contains it.
