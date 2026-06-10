#!/bin/sh
# HELP: Install the portable boot animation hook.
# ICON: bootanim
# GRID: BootAnim Install

[ -f /opt/muos/script/var/func.sh ] && . /opt/muos/script/var/func.sh

COMMON_DIR="/run/muos/storage/application/bootanim_common"
[ -d "$COMMON_DIR" ] || COMMON_DIR="/mnt/mmc/MUOS/application/bootanim_common"
[ -d "$COMMON_DIR" ] || COMMON_DIR="/mnt/sdcard/MUOS/application/bootanim_common"

cd "$COMMON_DIR" 2>/dev/null || exit 1
exec ./bootanim-manager.sh install
