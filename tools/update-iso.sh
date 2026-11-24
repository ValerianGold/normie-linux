#!/bin/bash
# The one command for "I have a new patch, give me a new ISO".
#
#   tools/update-iso.sh ~/Downloads/0010-*.patch              apply the patch(es), check, rebuild the ISO
#   tools/update-iso.sh                                        no patch: check and rebuild what is in the repo
#   tools/update-iso.sh --profile Normie-Live PATCH...         another profile (default: Normie-Full-Live)
#   tools/update-iso.sh --no-build PATCH...                    apply and check, but do not build
#
# Run it as yourself, from any folder (it asks for your password when it needs administrator rights).
# It stops at the FIRST problem and says what to do; nothing after a failed step runs:
#   1 apply the patch(es); one that is already applied is skipped, not an error
#   2 run the automated tests
#   3 check the image description is sound
#   4 check every package name exists            (saved to ~/normie-linux-out/preflight.txt)
#   5 check the whole package set installs together
#   6 build the ISO; the previous ISO is kept in ~/normie-linux-out/isos/
#
# A patch only changes the source. The ISO changes only when this script (or tools/build.sh) builds it.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

USER_HOME="$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)"
OUTDIR="${NORMIE_OUT:-$USER_HOME/normie-linux-out}"
SUDO=sudo
{ [ "$EUID" -eq 0 ] || [ "${NORMIE_TEST:-0}" = 1 ]; } && SUDO=""

step() { echo; echo "[$1/6] $2"; }
die() { echo >&2; echo "STOPPED: $1" >&2; [ -n "${2:-}" ] && echo "$2" >&2; exit 1; }


main() {
	PROFILE=Normie-Full-Live
	BUILD=1
	PATCHES=()
	while [ $# -gt 0 ]; do
		case "$1" in
			--profile) PROFILE="${2:-}"; shift ;;
			--no-build) BUILD=0 ;;
			-h|--help) sed -n '2,19p' "${BASH_SOURCE[0]}"; exit 0 ;;
			-*) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
			*) PATCHES+=("$1") ;;
		esac
		shift
	done

	# ---------------------------------------------------------------- 1 patches
	step 1 "Applying patches"
	AM_DIR="$(git rev-parse --git-path rebase-apply)"
	if [ -d "$AM_DIR" ]; then
		if [ -f "$AM_DIR/applying" ]; then
			echo "Found a half-finished earlier patch attempt; clearing it."
			git am --abort >/dev/null 2>&1 || die "Could not clear the earlier half-finished patch attempt." "Run: git am --abort    and tell me what it says."
		else
			die "Git is in the middle of something else (a rebase)." "Tell me and I will help you finish or cancel it."
		fi
	fi
	[ "${#PATCHES[@]}" -eq 0 ] && echo "No patch given; using the repository as it is."
	for patch in "${PATCHES[@]}"; do
		[ -f "$patch" ] || die "Cannot find the patch file: $patch" "Check the name. Downloads normally land in ~/Downloads."
		# the patch's one-line title (git may fold a long one over several lines)
		subject="$(awk '/^Subject: /{f=1; sub(/^Subject: (\[PATCH[^]]*\] )?/,""); printf "%s",$0; next}
		                f&&/^[ \t]/{sub(/^[ \t]+/," "); printf "%s",$0; next} f{exit}' "$patch")"
		if [ -n "$subject" ] && git log --format=%s | grep -Fxq -- "$subject"; then
			echo "Already applied, skipping: $subject"
			continue
		fi
		if git am "$patch"; then
			echo "Applied: ${subject:-$patch}"
		else
			git am --abort >/dev/null 2>&1
			die "The patch did not apply: $patch" "Nothing was changed. Send me the message above."
		fi
	done

	# ---------------------------------------------------------------- 2-3 tests and structure
	step 2 "Running the automated tests"
	python3 -m unittest discover -s tests || die "The automated tests failed." "Send me the output above before building anything."

	step 3 "Checking the image description"
	python3 tools/validate-kiwi.py || die "The image description has a structural problem." "Send me the output above."

	# ---------------------------------------------------------------- 4-5 packages
	step 4 "Checking that every package name exists on Fedora"
	mkdir -p "$OUTDIR"
	python3 tools/check-packages.py 2>&1 | tee "$OUTDIR/preflight.txt"
	[ "${PIPESTATUS[0]}" -eq 0 ] || die "Some package names do not exist, so a build would fail." "Send me: $OUTDIR/preflight.txt"

	step 5 "Checking that all the packages can be installed together"
	$SUDO python3 tools/solve-check.py "$PROFILE" || die "The packages conflict or cannot be resolved." "Send me the lines above (the full output is in solve-check.log)."

	# ---------------------------------------------------------------- 6 build
	if [ "$BUILD" -eq 0 ]; then
		echo; echo "Checks passed. Skipping the build as requested (--no-build)."
		exit 0
	fi
	step 6 "Building the ISO ($PROFILE). This takes a while."
	tools/build.sh "$PROFILE" || die "The build failed." "The full log is $OUTDIR/$PROFILE.log; the last lines are shown above. Send me those."

	echo
	echo "All done. Boot the new ISO in the VM to try it. A system you installed earlier does NOT change;"
	echo "only a system installed from this new ISO has these changes."
}

main "$@"
exit $?
