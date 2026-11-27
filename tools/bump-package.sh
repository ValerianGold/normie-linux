#!/bin/bash
# Raise a package's release number and add a changelog line, so installed systems see an update.
#
#   tools/bump-package.sh PACKAGE "what changed"
#   e.g.  tools/bump-package.sh normie-logos "New logo"
#
# PACKAGE is one of the folders under packaging/ (normie-logos, normie-tools, ...). Run it for every package whose
# files you changed, then commit, push and run tools/publish-packages.sh. It only edits that package's .spec file
# (Release: 1 becomes 2, plus a %changelog line dated today) and is not run by any build.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pkg="${1:-}"
note="${2:-}"
if ! [[ "$pkg" =~ ^[a-z0-9][a-z0-9-]*$ ]] || [ -z "$note" ]; then
	echo 'Usage: tools/bump-package.sh PACKAGE "what changed"   (for example: tools/bump-package.sh normie-logos "New logo")' >&2
	echo "Packages: $(cd "$ROOT/packaging" && ls -d normie-*/ 2>/dev/null | tr -d / | tr '\n' ' ')" >&2
	exit 2
fi
case "$note" in *$'\n'*) echo "The note must be one line." >&2; exit 2;; esac
SPEC="$ROOT/packaging/$pkg/$pkg.spec"
[ -f "$SPEC" ] || { echo "No such package: $pkg (no $SPEC)" >&2; exit 1; }

rel_line="$(grep -E '^Release:[[:space:]]+[0-9]+%\{\?dist\}[[:space:]]*$' "$SPEC" | head -n1 || true)"
[ -n "$rel_line" ] || { echo "Cannot find a 'Release: N%{?dist}' line in $SPEC; nothing was changed." >&2; exit 1; }
old="$(echo "$rel_line" | sed -E 's/^Release:[[:space:]]+([0-9]+).*/\1/')"
new=$((old + 1))

ver="$(grep -E '^Version:[[:space:]]+' "$SPEC" | head -n1 | sed -E 's/^Version:[[:space:]]+//; s/[[:space:]]+$//')"
if [[ "$ver" =~ ^%\{([A-Za-z0-9_]+)\}$ ]]; then          # Version comes from a %global such as tools_version
	ver="$(grep -E "^%global[[:space:]]+${BASH_REMATCH[1]}[[:space:]]+" "$SPEC" | head -n1 | awk '{print $3}')"
fi
[[ "$ver" =~ ^[0-9][A-Za-z0-9._+~]*$ ]] || { echo "Cannot work out the version of $pkg; nothing was changed." >&2; exit 1; }
grep -q '^%changelog' "$SPEC" || { echo "$SPEC has no %changelog; nothing was changed." >&2; exit 1; }

stamp="$(LC_ALL=C date '+%a %b %-d %Y')"
entry="* $stamp Normie Linux contributors <noreply@invalid> - $ver-$new"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
awk -v new="$new" -v entry="$entry" -v note="- $note" '
	/^Release:[ \t]+[0-9]+%\{\?dist\}[ \t]*$/ && !done_rel { print "Release:        " new "%{?dist}"; done_rel=1; next }
	{ print }
	/^%changelog/ { print entry; print note }
' "$SPEC" > "$tmp"
cat "$tmp" > "$SPEC"
echo "$pkg: Release $old -> $new  ($ver-$new)"
