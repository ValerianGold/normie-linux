#!/bin/bash
# Boot the newest ISO in a virtual machine, to look at it before anyone else does.
#
#   tools/try-iso.sh                 boot the newest Normie-Full-Live ISO (live session, and install onto a fresh virtual disk)
#   tools/try-iso.sh --installed     boot the virtual disk only (after you installed), without the ISO
#   tools/try-iso.sh --fresh         throw the virtual disk away and start again
#   tools/try-iso.sh --iso FILE      use a particular ISO
#   tools/try-iso.sh --print         show the command instead of running it
#
# Needs, once:   sudo dnf install qemu-system-x86 edk2-ovmf
# The virtual disk (40 GB, grows only as it fills) is ~/normie-linux-out/vm/. Memory and cores: NORMIE_VM_MEM (default 6G), NORMIE_VM_CPUS (default 4).
# Close the window to power the machine off. Nothing here touches your real disks.
set -eu

OUT="${NORMIE_OUT:-$HOME/normie-linux-out}"
VMDIR="$OUT/vm"
DISK="$VMDIR/normie-test.qcow2"
VARS="$VMDIR/OVMF_VARS.fd"
ISO=""
INSTALLED=0
FRESH=0
PRINT=0

while [ $# -gt 0 ]; do
	case "$1" in
		--installed) INSTALLED=1 ;;
		--fresh) FRESH=1 ;;
		--print) PRINT=1 ;;
		--iso) ISO="${2:-}"; shift ;;
		-h|--help) sed -n '2,11p' "${BASH_SOURCE[0]}"; exit 0 ;;
		*) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
	esac
	shift
done

first_existing() { for f in "$@"; do [ -e "$f" ] && { echo "$f"; return 0; }; done; return 1; }

QEMU="$(command -v qemu-system-x86_64 || true)"
CODE="$(first_existing "${NORMIE_OVMF_CODE:-/nonexistent}" /usr/share/edk2/ovmf/OVMF_CODE.fd /usr/share/edk2/ovmf/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd || true)"
TEMPLATE="$(first_existing "${NORMIE_OVMF_VARS:-/nonexistent}" /usr/share/edk2/ovmf/OVMF_VARS.fd /usr/share/edk2/ovmf/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd || true)"
if [ -z "$QEMU" ] || [ -z "$CODE" ] || [ -z "$TEMPLATE" ]; then
	echo "STOPPED: the virtual machine tools are not installed." >&2
	echo "Install them once with:   sudo dnf install qemu-system-x86 edk2-ovmf" >&2
	exit 1
fi

if [ "$INSTALLED" -eq 0 ] && [ -z "$ISO" ]; then
	ISO="$(ls -t "$OUT"/Normie-Full-Live-build/*.iso 2>/dev/null | head -n1 || true)"
	[ -n "$ISO" ] || { echo "STOPPED: no ISO found in $OUT/Normie-Full-Live-build/. Build one first (tools/update-iso.sh)." >&2; exit 1; }
fi
if [ "$INSTALLED" -eq 0 ] && [ ! -f "$ISO" ]; then
	echo "STOPPED: cannot find the ISO: $ISO" >&2
	exit 1
fi

mkdir -p "$VMDIR"
if [ "$FRESH" -eq 1 ]; then rm -f -- "$DISK" "$VARS"; fi
if [ ! -f "$DISK" ]; then
	if [ "$INSTALLED" -eq 1 ]; then echo "STOPPED: there is no installed virtual disk yet. Run without --installed first." >&2; exit 1; fi
	[ "$PRINT" -eq 1 ] || qemu-img create -q -f qcow2 "$DISK" 40G
fi
[ -f "$VARS" ] || [ "$PRINT" -eq 1 ] || cp "$TEMPLATE" "$VARS"

ARGS=(-machine q35 -m "${NORMIE_VM_MEM:-6G}" -smp "${NORMIE_VM_CPUS:-4}"
	-drive "if=pflash,format=raw,readonly=on,file=$CODE"
	-drive "if=pflash,format=raw,file=$VARS"
	-drive "file=$DISK,if=virtio,format=qcow2"
	-device virtio-vga -display gtk
	-device qemu-xhci -device usb-tablet
	-nic user,model=virtio-net-pci
	-name "Normie Linux test")
if [ -w /dev/kvm ]; then ARGS+=(-enable-kvm -cpu host); else echo "Note: no /dev/kvm access, so this will be slow." >&2; fi
[ "$INSTALLED" -eq 1 ] || ARGS+=(-drive "file=$ISO,media=cdrom,readonly=on,if=none,id=iso" -device "ide-cd,drive=iso,bootindex=0")

if [ "$PRINT" -eq 1 ]; then
	printf '%q ' "$QEMU" "${ARGS[@]}"; echo
	exit 0
fi
echo "Starting the virtual machine${ISO:+ from $ISO}. Close its window to power it off."
exec "$QEMU" "${ARGS[@]}"
