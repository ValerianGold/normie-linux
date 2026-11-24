#!/bin/bash
# Build the Normie Linux packages (the four under packaging/) into a local package repository
# that the image build reads. This is how our own release files, logos, wallpaper and Plasma look
# get into the ISO in place of Fedora's.
#
#   tools/build-rpms.sh              build them now
#   tools/build-rpms.sh --if-needed  build only if packaging/ (or the project address) changed
#
# Needs two tools, once:   sudo dnf install rpm-build createrepo_c
# The repository goes to /var/lib/normie-linux/rpms (override with NORMIE_LOCAL_REPO). Nothing in it
# is ever put on an installed system: it is only a place for the image build to read from.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_REPO="${NORMIE_LOCAL_REPO:-/var/lib/normie-linux/rpms}"
IF_NEEDED=0
case "${1:-}" in
	"") ;;
	--if-needed) IF_NEEDED=1 ;;
	-h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
	*) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

SUDO=sudo
{ [ "$EUID" -eq 0 ] || [ "${NORMIE_TEST:-0}" = 1 ]; } && SUDO=""

cd "$REPO"
SPECS=(packaging/*/*.spec)
[ -e "${SPECS[0]}" ] || { echo "No packages found under packaging/." >&2; exit 1; }

# The project's public address (set by tools/set-github-user.sh) goes into /etc/os-release.
HOME_URL="$(sed -n 's#.*<contact>\(https\?://[^<]*\)</contact>.*#\1#p' Normie-Linux.kiwi | head -n1)"
DEFINES=()
if [ -n "$HOME_URL" ]; then
	DEFINES=(--define "normie_home_url $HOME_URL")
else
	echo "Note: the project address is not set yet (tools/set-github-user.sh), so /etc/os-release will"
	echo "      point at https://github.com for now."
fi

# A fingerprint of everything that goes into the packages
FINGERPRINT="$( { find packaging -type f -print0 | sort -z | xargs -0 sha256sum; echo "url=$HOME_URL"; } | sha256sum | cut -d' ' -f1)"
if [ "$IF_NEEDED" -eq 1 ] && [ "$(cat "$LOCAL_REPO/.source-fingerprint" 2>/dev/null || true)" = "$FINGERPRINT" ] \
		&& [ -d "$LOCAL_REPO/repodata" ]; then
	echo "The Normie packages are up to date ($LOCAL_REPO)."
	exit 0
fi

missing=()
for tool in rpmbuild createrepo_c; do command -v "$tool" >/dev/null 2>&1 || missing+=("$tool"); done
if [ "${#missing[@]}" -gt 0 ]; then
	echo "STOPPED: this needs ${missing[*]}, which is not installed." >&2
	echo "Install them once with:   sudo dnf install rpm-build createrepo_c" >&2
	exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/normie-rpms-XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/top" "$WORK/repo"

echo "Building the Normie Linux packages..."
for spec in "${SPECS[@]}"; do
	dir="$(cd "$(dirname "$spec")" && pwd)"
	echo "  $(basename "$spec")"
	rpmbuild -bb "$spec" --quiet \
		--define "_topdir $WORK/top" \
		--define "_sourcedir $dir" \
		"${DEFINES[@]}" >"$WORK/build.log" 2>&1 || {
			echo "STOPPED: building $(basename "$spec") failed. rpmbuild said:" >&2
			tail -n 40 "$WORK/build.log" >&2
			exit 1
		}
done

find "$WORK/top/RPMS" -name '*.rpm' -exec cp -t "$WORK/repo" {} +
built="$(find "$WORK/repo" -name '*.rpm' | wc -l)"
if [ "$built" -ne "${#SPECS[@]}" ]; then
	echo "STOPPED: expected ${#SPECS[@]} packages but built $built." >&2
	exit 1
fi
createrepo_c --quiet "$WORK/repo"
echo "$FINGERPRINT" > "$WORK/repo/.source-fingerprint"
chmod -R a+rX "$WORK/repo"

# Replace the published copy in one step
$SUDO mkdir -p "$(dirname "$LOCAL_REPO")"
$SUDO rm -rf -- "$LOCAL_REPO.new"
$SUDO cp -a "$WORK/repo" "$LOCAL_REPO.new"
$SUDO rm -rf -- "$LOCAL_REPO"
$SUDO mv "$LOCAL_REPO.new" "$LOCAL_REPO"

echo "Built $built packages into $LOCAL_REPO:"
( cd "$LOCAL_REPO" && ls -1 ./*.rpm | sed 's#^\./#  #' )
