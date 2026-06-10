#!/bin/sh
# Knulli / Batocera early boot hook for banim.
# Starts bootanim as soon as /dev/fb0 exists.
# Stops when another process opens /dev/fb0.

BOOTANIM_DIR="/boot/bootanim"
BOOTANIM_BIN="$BOOTANIM_DIR/bootanim"
BOOTANIM_FILE="$BOOTANIM_DIR/bootanim.banim"
LOG_FILE="/tmp/bootanim.log"
STOP_FILE="/tmp/bootanim.stop"

SCALE="2"
LOOP_START="180"
MAX_SECONDS="120"

rm -f "$STOP_FILE" 2>/dev/null
: > "$LOG_FILE" 2>/dev/null

[ -x "$BOOTANIM_BIN" ] || exit 0
[ -f "$BOOTANIM_FILE" ] || exit 0

"$BOOTANIM_BIN" \
    "$BOOTANIM_FILE" \
    --fb /dev/fb0 \
    --scale "$SCALE" \
    --loop-start "$LOOP_START" \
    --max-seconds "$MAX_SECONDS" \
    --stop-file "$STOP_FILE" \
    --wait-fb \
    --wait-fb-ms 8000 \
    --stop-on-any-fb-owner \
    --min-runtime-ms 1200 \
    --fb-owner-confirm-ms 75 \
    >> "$LOG_FILE" 2>&1 &

exit 0
