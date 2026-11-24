#!/bin/bash
# Record exactly which version of the project an ISO is built from. tools/build.sh runs this
# before every build; the file lands inside the ISO at /usr/share/normie/build-info, so any
# installed system (or live session) can say what it was built from:
#
#   cat /usr/share/normie/build-info
#
# Usage: tools/write-build-info.sh [PROFILE]
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${1:-unknown}"
OUT="$ROOT/root/usr/share/normie/build-info"

# safe.directory lets this work when the build runs as root inside a repository owned by you
g() { git -C "$ROOT" -c safe.directory="$ROOT" "$@" 2>/dev/null; }

commit="$(g rev-parse --short=12 HEAD)"; commit="${commit:-unknown}"
subject="$(g log -1 --format=%s | tr -d '"`$\\' | cut -c1-120)"
dirty=no
[ -n "$(g status --porcelain)" ] && dirty=yes

mkdir -p "$(dirname "$OUT")"
{
	echo "NORMIE_BUILD_PROFILE=$PROFILE"
	echo "NORMIE_BUILD_COMMIT=$commit"
	echo "NORMIE_BUILD_SUBJECT=\"$subject\""
	echo "NORMIE_BUILD_UNCOMMITTED_CHANGES=$dirty"
	echo "NORMIE_BUILD_DATE=$(date -u +%Y-%m-%dT%H:%MZ)"
} > "$OUT"
chmod 644 "$OUT"
