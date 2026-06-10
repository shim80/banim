#!/bin/sh
# HELP: Remove the boot animation hook and restore saved logos.
# ICON: bootanim
# GRID: BootAnim Uninstall

[ -f /opt/muos/script/var/func.sh ] && . /opt/muos/script/var/func.sh

COMMON_DIR="/run/muos/storage/application/bootanim_common"
[ -d "$COMMON_DIR" ] || COMMON_DIR="/mnt/mmc/MUOS/application/bootanim_common"
[ -d "$COMMON_DIR" ] || COMMON_DIR="/mnt/sdcard/MUOS/application/bootanim_common"

cd "$COMMON_DIR" 2>/dev/null || exit 1
exec ./bootanim-manager.sh uninstall
