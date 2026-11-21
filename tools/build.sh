#!/bin/bash
# Normie Linux build wrapper.
#
#   tools/build.sh                    build Normie-Live (Milestone 1)
#   tools/build.sh Normie-Full-Live   build the full ISO (Milestone 2)
#   tools/build.sh KDE-Desktop-Live   build the untouched Fedora KDE baseline
#
# Everything lands outside the repo, in ~/normie-linux-out (override with
# NORMIE_OUT=/some/dir). The full log of each build is saved next to the ISO
# so it can be pasted when something fails:
#   ~/normie-linux-out/<profile>.log
set -euo pipefail

PROFILE="${1:-Normie-Live}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$PROFILE" in
	Normie-*-Live|Normie-Live) KIWI_FILE="Normie-Linux.kiwi" ;;
	KDE-Desktop-Live)          KIWI_FILE="Fedora.kiwi" ;;
	*) echo "Unknown profile '$PROFILE'. Use Normie-Live, Normie-Full-Live or KDE-Desktop-Live." >&2; exit 2 ;;
esac

# kiwi needs root; re-run ourselves through sudo, remembering whose home to use
if [ "$EUID" -ne 0 ]; then
	exec sudo NORMIE_USER="$USER" NORMIE_OUT="${NORMIE_OUT:-}" "$0" "$@"
fi
BUILD_USER="${NORMIE_USER:-${SUDO_USER:-root}}"
USER_HOME="$(getent passwd "$BUILD_USER" | cut -d: -f6)"
OUT="${NORMIE_OUT:-$USER_HOME/normie-linux-out}"
mkdir -p "$OUT"
LOG="$OUT/$PROFILE.log"

cd "$REPO_DIR"
echo "Profile : $PROFILE"
echo "Kiwi    : $KIWI_FILE"
echo "Output  : $OUT/$PROFILE-build/"
echo "Log     : $LOG"
echo

set +e
./kiwi-build \
	--kiwi-file="$KIWI_FILE" \
	--image-type=iso \
	--image-profile="$PROFILE" \
	--output-dir="$OUT/$PROFILE" \
	--debug 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

chown -R "$BUILD_USER": "$OUT" 2>/dev/null || true

if [ "$STATUS" -ne 0 ]; then
	echo
	echo "BUILD FAILED (exit $STATUS). Last 60 lines of the log:"
	tail -n 60 "$LOG"
	echo
	echo "Full log: $LOG"
	exit "$STATUS"
fi

ISO="$(find "$OUT/$PROFILE-build" -maxdepth 1 -name '*.iso' | head -n1)"
echo
echo "BUILD OK"
echo "ISO    : $ISO"
[ -n "$ISO" ] && sha256sum "$ISO" | tee "$ISO.sha256"
