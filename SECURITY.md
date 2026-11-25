# Security

Normie Linux is **alpha software**. Please do not rely on it for anything sensitive yet.

To report a vulnerability, use GitHub's private reporting: open this repository's **Security** tab and
choose **Report a vulnerability**. Please do not open a public issue for security problems.

Areas that deserve the most scrutiny, because they run with administrator rights:
`packaging/normie-tools/files/usr/libexec/normie/` (the Update & Repair tools) and the package list they download
(`dist/normie-deps.list`, see `docs/UPDATE-AND-REPAIR.md` for how it is restricted).
