#!/bin/bash
# Pack one package folder under packaging/ into the source tarball its spec file names (Source0).
#
#   tools/pack-sources.sh packaging/normie-logos /some/sources/folder
#
# The tarball holds everything in the folder except the .spec itself, and is called <folder name>-sources.tar.gz.
# Used by tools/build-rpms.sh (the ISO build) and tools/build-srpms.sh (what is uploaded to the package repository),
# so both build from exactly the same files.
set -euo pipefail
dir="${1:-}"; dest="${2:-}"
if [ -z "$dir" ] || [ -z "$dest" ] || [ ! -d "$dir" ]; then
	echo "Usage: tools/pack-sources.sh PACKAGE-FOLDER DESTINATION-FOLDER" >&2
	exit 2
fi
name="$(basename "$(cd "$dir" && pwd)")"
mkdir -p "$dest"
tar -C "$dir" --exclude='*.spec' --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-01-01 00:00:00' \
	-czf "$dest/$name-sources.tar.gz" .
echo "$dest/$name-sources.tar.gz"
