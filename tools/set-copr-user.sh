#!/bin/bash
# Point this project at YOUR Copr package repository. Run once, after creating the Copr project:
#
#   tools/set-copr-user.sh COPR-USERNAME [PROJECT-NAME]        (PROJECT-NAME defaults to normie-linux)
#
# It writes the repository address into packaging/normie-release/normie.repo (which the release package
# installs on every new system, switched on) and remembers the names in packaging/copr.conf for
# tools/publish-packages.sh. It changes nothing else and is safe to run again.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOFILE="$ROOT/packaging/normie-release/normie.repo"
CONF="$ROOT/packaging/copr.conf"
owner="${1:-}"
project="${2:-normie-linux}"

if ! [[ "$owner" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || ! [[ "$project" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]]; then
	echo "Usage: tools/set-copr-user.sh YOUR-COPR-USERNAME [PROJECT-NAME]" >&2
	echo "(letters, numbers, dots, hyphens and underscores only; nothing was changed)" >&2
	exit 2
fi
[ -w "$REPOFILE" ] || { echo "Cannot write $REPOFILE" >&2; exit 1; }

# the file starts from a template with OWNER/PROJECT, or from an earlier run: rewrite both lines either way
sed -i -E \
	-e "s#^(baseurl=https://download\.copr\.fedorainfracloud\.org/results/)[^/]+/[^/]+/#\1$owner/$project/#" \
	-e "s#^(gpgkey=https://download\.copr\.fedorainfracloud\.org/results/)[^/]+/[^/]+/#\1$owner/$project/#" \
	-e "s#^enabled=.*#enabled=1#" \
	-e "s#^\# This file is filled in by .*#\# Filled in by tools/set-copr-user.sh.#" \
	-e "/^\# Until then the repository is switched off\.$/d" \
	"$REPOFILE"
grep -q "/results/$owner/$project/fedora-" "$REPOFILE" && grep -q "/results/$owner/$project/pubkey.gpg" "$REPOFILE" \
	|| { echo "Could not fill in $REPOFILE; it looks different from what I expected." >&2; exit 1; }

printf 'COPR_OWNER=%s\nCOPR_PROJECT=%s\n' "$owner" "$project" > "$CONF"

echo "Done."
echo "  Copr project:        $owner/$project"
echo "  Repository address:  https://download.copr.fedorainfracloud.org/results/$owner/$project/"
echo
echo "Next: run the tests, commit it, then publish the packages (docs/PACKAGE-REPOSITORY.md)."
