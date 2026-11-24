#!/bin/bash
# Normie Linux build wrapper.
#
#   tools/build.sh                    build Normie-Live (Milestone 1)
#   tools/build.sh Normie-Full-Live   build the full ISO (Milestone 2)
#   tools/build.sh KDE-Desktop-Live   build the untouched Fedora KDE baseline
#
# Everything lands outside the repo, in ~/normie-linux-out (override with
# NORMIE_OUT=/some/dir):
#   <profile>-build/              the newest build (the ISO, plus BUILD-INFO.txt saying what it was built from)
#   isos/                         every ISO ever built, named with its commit, e.g. Normie-Linux-Normie-Full-Live-45-ab12cd34ef56.iso
#   <profile>.log                 the full log of the latest build, to paste when something fails
# A patch only changes the SOURCE. An ISO changes only when you run this script again.
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

# Record which version of the project this build is made from (it goes inside the ISO)
"$REPO_DIR/tools/write-build-info.sh" "$PROFILE"
chown -R "$BUILD_USER": "$REPO_DIR/root/usr/share/normie" 2>/dev/null || true
INFO="$REPO_DIR/root/usr/share/normie/build-info"
info_get() { sed -n "s/^$1=//p" "$INFO" | tr -d '"'; }
COMMIT="$(info_get NORMIE_BUILD_COMMIT)"
DIRTY_TAG=""; [ "$(info_get NORMIE_BUILD_UNCOMMITTED_CHANGES)" = yes ] && DIRTY_TAG="-uncommitted"

# kiwi will not build into a folder that already holds an earlier build, and Fedora's build script
# never clears it. Keep any earlier ISO (a hard link costs no extra disk space), then clear the folder.
BUILD_DIR="$OUT/$PROFILE-build"
ARCHIVE="$OUT/isos"
mkdir -p "$ARCHIVE"
if [ -d "$BUILD_DIR" ]; then
	case "$BUILD_DIR" in "$OUT"/*-build) ;; *) echo "Refusing to clear unexpected folder: $BUILD_DIR" >&2; exit 2 ;; esac
	for old in "$BUILD_DIR"/*.iso; do
		[ -e "$old" ] || continue
		if [ -n "$(find "$ARCHIVE" -maxdepth 1 -samefile "$old" -print -quit 2>/dev/null)" ]; then
			echo "The previous ISO is already kept in $ARCHIVE"
			continue
		fi
		keep="$ARCHIVE/$(basename "${old%.iso}")-$PROFILE-earlier-$(date -r "$old" +%Y%m%d-%H%M).iso"
		if [ -e "$keep" ] || ln "$old" "$keep" 2>/dev/null; then
			echo "Kept the previous ISO as: $keep"
		else
			echo "Could not keep the previous ISO ($old). Move it somewhere safe, then run this again." >&2
			exit 1
		fi
	done
	rm -rf -- "$BUILD_DIR"
fi

echo "Profile : $PROFILE"
echo "Version : commit ${COMMIT}${DIRTY_TAG}"
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

ISO="$(find "$BUILD_DIR" -maxdepth 1 -name '*.iso' | head -n1)"
echo
echo "BUILD OK"
if [ -n "$ISO" ]; then
	cp "$INFO" "$BUILD_DIR/BUILD-INFO.txt"
	NAMED="$ARCHIVE/$(basename "${ISO%.iso}")-$PROFILE-$COMMIT$DIRTY_TAG.iso"
	ln -f "$ISO" "$NAMED" 2>/dev/null || echo "(could not add a named copy in $ARCHIVE)"
	chown -R "$BUILD_USER": "$OUT" 2>/dev/null || true
	echo "ISO     : $ISO"
	echo "Built from commit ${COMMIT}${DIRTY_TAG} (also kept as $NAMED)"
	sha256sum "$ISO" | tee "$ISO.sha256"
fi
