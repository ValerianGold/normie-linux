#!/bin/bash
# Point this project at YOUR GitHub copy of it. Run once, after creating the repository on GitHub:
#
#   tools/set-github-user.sh YOUR-USERNAME [REPO-NAME]        (REPO-NAME defaults to normie-linux)
#
# It sets, in two files:
#   packaging/normie-tools/files/etc/normie/update.conf   DEPS_LIST_URL  (where installed systems fetch the dependency list)
#   Normie-Linux.kiwi             <contact>      (the project's public address)
# It changes nothing else and is safe to run again.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$ROOT/packaging/normie-tools/files/etc/normie/update.conf"
KIWI="$ROOT/Normie-Linux.kiwi"
user="${1:-}"
repo="${2:-normie-linux}"

if ! [[ "$user" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$ ]] || ! [[ "$repo" =~ ^[A-Za-z0-9._-]{1,100}$ ]]; then
	echo "Usage: tools/set-github-user.sh YOUR-GITHUB-USERNAME [REPO-NAME]" >&2
	echo "(letters, numbers and hyphens only; nothing was changed)" >&2
	exit 2
fi
for f in "$CONF" "$KIWI"; do [ -w "$f" ] || { echo "Cannot write $f" >&2; exit 1; }; done
grep -q '^DEPS_LIST_URL=' "$CONF" || { echo "No DEPS_LIST_URL line found in $CONF" >&2; exit 1; }
grep -q '<contact>.*</contact>' "$KIWI" || { echo "No <contact> line found in $KIWI" >&2; exit 1; }

list_url="https://raw.githubusercontent.com/$user/$repo/main/dist/normie-deps.list"
home_url="https://github.com/$user/$repo"
sed -i "s#^DEPS_LIST_URL=.*#DEPS_LIST_URL=\"$list_url\"#" "$CONF"
sed -i "s#<contact>.*</contact>#<contact>$home_url</contact>#" "$KIWI"

echo "Done."
echo "  Update list address: $list_url"
echo "  Project address:     $home_url"
echo
echo "Next: commit it, push it, then open the list address in your browser to confirm it shows the package list."
