#!/bin/bash
# Build the source packages and send them to your Copr project, which builds and signs the real ones.
#
#   tools/publish-packages.sh
#
# Needs once:   sudo dnf install rpm-build copr-cli      and your Copr API token saved in ~/.config/copr
# (docs/PACKAGE-REPOSITORY.md explains both), and tools/set-copr-user.sh run first.
# Remember: a package only reaches installed systems if its Version or Release number went UP.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$REPO/packaging/copr.conf"
[ -r "$CONF" ] || { echo "STOPPED: no Copr project set. Run  tools/set-copr-user.sh YOUR-COPR-USERNAME  first." >&2; exit 1; }
# shellcheck disable=SC1090
. "$CONF"
[ -n "${COPR_OWNER:-}" ] && [ -n "${COPR_PROJECT:-}" ] || { echo "STOPPED: $CONF is incomplete; run tools/set-copr-user.sh again." >&2; exit 1; }
command -v copr-cli >/dev/null 2>&1 || { echo "STOPPED: copr-cli is not installed. Install it once with:   sudo dnf install copr-cli" >&2; exit 1; }
[ -s "$HOME/.config/copr" ] || { echo "STOPPED: your Copr API token is not saved in ~/.config/copr (docs/PACKAGE-REPOSITORY.md, step 3)." >&2; exit 1; }

"$REPO/tools/build-srpms.sh"
OUT="${NORMIE_OUT:-$HOME/normie-linux-out}/srpms"
echo
echo "Sending them to Copr project $COPR_OWNER/$COPR_PROJECT (each build takes a few minutes)..."
for srpm in "$OUT"/*.src.rpm; do
	echo "  $(basename "$srpm")"
	copr-cli build "$COPR_OWNER/$COPR_PROJECT" "$srpm"
done
echo
echo "Done. Packages are signed and published by Copr: https://copr.fedorainfracloud.org/coprs/$COPR_OWNER/$COPR_PROJECT/"
