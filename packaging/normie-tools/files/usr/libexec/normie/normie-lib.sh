# normie-lib.sh: helpers shared by normie-update and normie-remind. Sourced, never run directly.

# normie_fetch_list URL OUTFILE
#   Download the dependency list at URL (https only) and write the VALID package names, one per
#   line, sorted and de-duplicated, to OUTFILE. Names only: a line must start with a letter or
#   digit (so it can never act as a command option) and contain only name characters; anything
#   else is ignored. Sets NORMIE_LIST_INVALID to the number of ignored lines.
#   Returns 0 on success, 1 if the URL is not https or the download fails, 2 if the list is
#   empty or implausibly large.
normie_fetch_list() {
	local url="$1" out="$2" raw line n
	NORMIE_LIST_INVALID=0
	case "$url" in https://*) ;; *) return 1 ;; esac
	raw="$(mktemp)" || return 1
	if ! curl -fsSL --max-time 30 --max-filesize 1048576 -o "$raw" "$url"; then rm -f "$raw"; return 1; fi
	: > "$out.tmp"
	while IFS= read -r line; do
		line="${line%%#*}"; line="${line//[[:space:]]/}"
		[ -z "$line" ] && continue
		if [[ "$line" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}$ ]]; then printf '%s\n' "$line" >> "$out.tmp"
		else NORMIE_LIST_INVALID=$(( NORMIE_LIST_INVALID + 1 )); fi
	done < "$raw"
	rm -f "$raw"
	LC_ALL=C sort -u "$out.tmp" > "$out"; rm -f "$out.tmp"
	n="$(wc -l < "$out")"
	[ "$n" -ge 1 ] && [ "$n" -le 3000 ] || return 2
	return 0
}

# normie_list_hash FILE: a fingerprint of a list produced by normie_fetch_list
normie_list_hash() { sha256sum "$1" | cut -d' ' -f1; }
