#!/bin/bash
# Build the source packages (.src.rpm) of the packages under packaging/. These are what gets uploaded to
# the package repository (tools/publish-packages.sh does that for you).
#
#   tools/build-srpms.sh
#
# Needs once:   sudo dnf install rpm-build
# Output: ~/normie-linux-out/srpms/   (override with NORMIE_OUT=/some/folder)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${NORMIE_OUT:-$HOME/normie-linux-out}/srpms"
command -v rpmbuild >/dev/null 2>&1 || { echo "STOPPED: rpmbuild is not installed. Install it once with:   sudo dnf install rpm-build" >&2; exit 1; }

HOME_URL="$(sed -n 's#.*<contact>\(https\?://[^<]*\)</contact>.*#\1#p' "$REPO/Normie-Linux.kiwi" | head -n1)"
DEFINES=()
[ -n "$HOME_URL" ] && DEFINES=(--define "normie_home_url $HOME_URL")

WORK="$(mktemp -d "${TMPDIR:-/tmp}/normie-srpms-XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/top" "$WORK/sources"
rm -rf -- "$OUT"; mkdir -p "$OUT"

shopt -s nullglob
SPECS=("$REPO"/packaging/*/*.spec)
[ "${#SPECS[@]}" -gt 0 ] || { echo "No packages found under packaging/." >&2; exit 1; }
echo "Building the source packages..."
for spec in "${SPECS[@]}"; do
	dir="$(dirname "$spec")"
	"$REPO/tools/pack-sources.sh" "$dir" "$WORK/sources" >/dev/null
	rpmbuild -bs "$spec" --quiet --define "_topdir $WORK/top" --define "_sourcedir $WORK/sources" \
		"${DEFINES[@]}" >"$WORK/build.log" 2>&1 || {
			echo "STOPPED: building the source package of $(basename "$spec") failed. rpmbuild said:" >&2
			tail -n 40 "$WORK/build.log" >&2
			exit 1
		}
done
cp -t "$OUT" "$WORK"/top/SRPMS/*.src.rpm
echo "Source packages in $OUT:"
ls -1 "$OUT" | sed 's/^/  /'
