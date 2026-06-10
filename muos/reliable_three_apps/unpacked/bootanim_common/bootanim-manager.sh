#!/bin/sh
# BootAnim Manager for muOS.
# Provides an explicit menu:
#   1. Install boot animation
#   2. Uninstall boot animation
#   3. Preview boot animation

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)"
[ -n "$APP_DIR" ] || APP_DIR="/run/muos/storage/application/bootanim_manager"

CONF_FILE="$APP_DIR/bootanim.conf"
LOG_FILE="/tmp/bootanim-manager.log"
PERSIST_LOG="/mnt/mmc/MUOS/bootanim-manager-last.log"

INSTALL_DIR="/opt/bootanim"
INSTALL_BIN="$INSTALL_DIR/bootanim"
INSTALL_ANIM="$INSTALL_DIR/bootanim.banim"
MARKER_FILE="$INSTALL_DIR/.installed_by_bootanim_manager"
HOOK_FILE="/opt/muos/script/init/S03bootanim"

APP_BIN="$APP_DIR/bin/bootanim"
APP_LOGO_TOOL="$APP_DIR/bin/banim_logo"

MUOS_LOGO_TARGET="/mnt/mmc/muoslogo.ico"
MUOS_BOOTLOGO_TARGET="/mnt/boot/bootlogo.bmp"

# Defaults. Can be overridden by bootanim.conf.
SCALE=2
LOOP_START=180
MAX_SECONDS=120
WAIT_FB_MS=8000
MIN_RUNTIME_MS=1200
FB_OWNER_CONFIRM_MS=75
BOOTLOGO_SIZE=640x480
MUOS_ICO_SIZE=256x256
PREVIEW_SECONDS=8

[ -f "$CONF_FILE" ] && . "$CONF_FILE"

log() {
    echo "BootAnim Manager: $1" >> "$LOG_FILE" 2>/dev/null
}

persist_log() {
    if [ -d /mnt/mmc/MUOS ]; then
        cp "$LOG_FILE" "$PERSIST_LOG" 2>/dev/null
    fi
}

reset_log() {
    : > "$LOG_FILE" 2>/dev/null
}

show_message() {
    # muOS app launches do not provide a normal terminal.
    # Keep this non-blocking; results are written to the persistent log.
    title="$1"
    msg="$2"
    log "$title: $msg"
    persist_log
}
choose_action() {
    # Not used in v6. muOS exposes each action as a separate app entry.
    return 1
}
find_animation_source() {
    for f in \
        "$APP_DIR/bootanim.banim" \
        "/run/muos/storage/application/bootanim_manager/bootanim.banim" \
        "/mnt/mmc/MUOS/bootanim/bootanim.banim" \
        "/mnt/sdcard/MUOS/bootanim/bootanim.banim" \
        "/opt/bootanim/bootanim.banim"
    do
        [ -f "$f" ] && [ -s "$f" ] && { echo "$f"; return 0; }
    done
    return 1
}

find_preview_animation() {
    if [ -f "$INSTALL_ANIM" ] && [ -s "$INSTALL_ANIM" ]; then
        echo "$INSTALL_ANIM"
        return 0
    fi
    find_animation_source
}

generate_logo_from_banim() {
    out_file="$1"
    out_size="$2"
    out_format="$3"

    [ -x "$APP_LOGO_TOOL" ] || {
        log "WARNING: missing logo helper $APP_LOGO_TOOL; logo unchanged"
        return 1
    }

    [ -f "$INSTALL_ANIM" ] || {
        log "WARNING: missing installed animation $INSTALL_ANIM; logo unchanged"
        return 1
    }

    "$APP_LOGO_TOOL" "$INSTALL_ANIM" "$out_file" --size "$out_size" --format "$out_format" >> "$LOG_FILE" 2>&1
}

backup_once() {
    src="$1"
    [ -e "$src" ] || return 0
    [ -e "$src.before-bootanim-manager" ] || cp "$src" "$src.before-bootanim-manager" 2>/dev/null
}

install_logo_files() {
    if [ -d /mnt/boot ]; then
        backup_once "$MUOS_BOOTLOGO_TARGET"
        if generate_logo_from_banim "$MUOS_BOOTLOGO_TARGET" "$BOOTLOGO_SIZE" bmp; then
            log "generated bootlogo BMP from .banim frame 0: $MUOS_BOOTLOGO_TARGET size=$BOOTLOGO_SIZE"
        else
            log "WARNING: could not generate $MUOS_BOOTLOGO_TARGET"
        fi
    else
        log "/mnt/boot not mounted; bootlogo.bmp unchanged"
    fi

    if [ -d /mnt/mmc ]; then
        backup_once "$MUOS_LOGO_TARGET"
        if generate_logo_from_banim "$MUOS_LOGO_TARGET" "$MUOS_ICO_SIZE" ico; then
            log "generated muOS ICO from .banim frame 0: $MUOS_LOGO_TARGET size=$MUOS_ICO_SIZE"
        else
            log "WARNING: could not generate $MUOS_LOGO_TARGET"
        fi
    else
        log "/mnt/mmc not mounted; muoslogo.ico unchanged"
    fi
}

restore_logo_files() {
    if [ -f "$MUOS_LOGO_TARGET.before-bootanim-manager" ]; then
        cp "$MUOS_LOGO_TARGET.before-bootanim-manager" "$MUOS_LOGO_TARGET" 2>/dev/null && \
            log "restored $MUOS_LOGO_TARGET"
    fi
    if [ -f "$MUOS_BOOTLOGO_TARGET.before-bootanim-manager" ]; then
        cp "$MUOS_BOOTLOGO_TARGET.before-bootanim-manager" "$MUOS_BOOTLOGO_TARGET" 2>/dev/null && \
            log "restored $MUOS_BOOTLOGO_TARGET"
    fi
}

install_bootanim() {
    reset_log
    log "install requested"
    log "app dir: $APP_DIR"

    if [ ! -x "$APP_BIN" ]; then
        log "ERROR: missing executable $APP_BIN"
        persist_log
        show_message "BootAnim Manager" "Install failed: missing executable.\n\nLog: $PERSIST_LOG"
        exit 0
    fi

    ANIM_SRC="$(find_animation_source)"
    if [ -z "$ANIM_SRC" ]; then
        log "ERROR: no bootanim.banim found"
        log "Place bootanim.banim in $APP_DIR or /mnt/mmc/MUOS/bootanim/bootanim.banim"
        persist_log
        show_message "BootAnim Manager" "Install failed: no bootanim.banim found.\n\nPlace it in:\n/mnt/mmc/MUOS/bootanim/bootanim.banim\n\nLog: $PERSIST_LOG"
        exit 0
    fi

    mkdir -p "$INSTALL_DIR" 2>/dev/null || {
        log "ERROR: cannot create $INSTALL_DIR"
        persist_log
        show_message "BootAnim Manager" "Install failed: cannot create $INSTALL_DIR.\n\nLog: $PERSIST_LOG"
        exit 0
    }

    cp "$APP_BIN" "$INSTALL_BIN" 2>/dev/null || {
        log "ERROR: cannot copy binary to $INSTALL_BIN"
        persist_log
        show_message "BootAnim Manager" "Install failed: cannot copy binary.\n\nLog: $PERSIST_LOG"
        exit 0
    }

    cp "$ANIM_SRC" "$INSTALL_ANIM" 2>/dev/null || {
        log "ERROR: cannot copy animation from $ANIM_SRC"
        persist_log
        show_message "BootAnim Manager" "Install failed: cannot copy animation.\n\nLog: $PERSIST_LOG"
        exit 0
    }

    chmod +x "$INSTALL_BIN" 2>/dev/null

    if [ -f "$HOOK_FILE" ] && ! grep -q 'installed_by_bootanim_manager' "$HOOK_FILE" 2>/dev/null; then
        cp "$HOOK_FILE" "$HOOK_FILE.before-bootanim-manager" 2>/dev/null
        log "backed up existing hook to $HOOK_FILE.before-bootanim-manager"
    fi

    cat > "$HOOK_FILE" <<EOF_HOOK
#!/bin/sh
# muOS portable boot animation hook.
# installed_by_bootanim_manager

case "\$1" in
    start)
        BOOTANIM_BIN="$INSTALL_BIN"
        BOOTANIM_FILE="$INSTALL_ANIM"
        LOG_FILE="/tmp/bootanim.log"
        STOP_FILE="/tmp/bootanim.stop"

        rm -f "\$STOP_FILE" 2>/dev/null
        : > "\$LOG_FILE" 2>/dev/null

        [ -x "\$BOOTANIM_BIN" ] || {
            echo "S03bootanim: missing or non-executable \$BOOTANIM_BIN" >> "\$LOG_FILE"
            exit 0
        }

        [ -f "\$BOOTANIM_FILE" ] || {
            echo "S03bootanim: missing animation \$BOOTANIM_FILE" >> "\$LOG_FILE"
            exit 0
        }

        "\$BOOTANIM_BIN" \\
            "\$BOOTANIM_FILE" \\
            --fb /dev/fb0 \\
            --scale $SCALE \\
            --loop-start $LOOP_START \\
            --max-seconds $MAX_SECONDS \\
            --stop-file "\$STOP_FILE" \\
            --wait-fb \\
            --wait-fb-ms $WAIT_FB_MS \\
            --stop-on-any-fb-owner \\
            --min-runtime-ms $MIN_RUNTIME_MS \\
            --fb-owner-confirm-ms $FB_OWNER_CONFIRM_MS \\
            >> "\$LOG_FILE" 2>&1 &
        ;;
esac

exit 0
EOF_HOOK

    chmod +x "$HOOK_FILE" 2>/dev/null
    install_logo_files
    echo "installed" > "$MARKER_FILE" 2>/dev/null
    sync

    log "installed successfully"
    log "animation source: $ANIM_SRC"
    log "scale=$SCALE loop_start=$LOOP_START bootlogo_size=$BOOTLOGO_SIZE muos_ico_size=$MUOS_ICO_SIZE"
    log "reboot to test"
    persist_log
    show_message "BootAnim Manager" "Boot animation installed.\n\nReboot to test.\n\nLog: $PERSIST_LOG"
}

uninstall_bootanim() {
    reset_log
    log "uninstall requested"

    if [ -f "$HOOK_FILE" ] && grep -q 'installed_by_bootanim_manager' "$HOOK_FILE" 2>/dev/null; then
        rm -f "$HOOK_FILE" 2>/dev/null
        log "removed $HOOK_FILE"
    else
        log "hook not managed by BootAnim Manager; left unchanged"
    fi

    restore_logo_files
    rm -f "$INSTALL_BIN" "$INSTALL_ANIM" "$MARKER_FILE" 2>/dev/null
    rmdir "$INSTALL_DIR" 2>/dev/null
    sync

    log "uninstalled successfully"
    persist_log
    show_message "BootAnim Manager" "Boot animation uninstalled.\n\nOriginal logos were restored if backups existed.\n\nLog: $PERSIST_LOG"
}

preview_bootanim() {
    reset_log
    log "preview requested"

    PREVIEW_ANIM="$(find_preview_animation)"
    if [ -z "$PREVIEW_ANIM" ]; then
        log "ERROR: no animation found for preview"
        persist_log
        show_message "BootAnim Manager" "Preview failed: no bootanim.banim found.\n\nPlace it in:\n/mnt/mmc/MUOS/bootanim/bootanim.banim\n\nLog: $PERSIST_LOG"
        exit 0
    fi

    if [ -x "$INSTALL_BIN" ]; then
        PREVIEW_BIN="$INSTALL_BIN"
    else
        PREVIEW_BIN="$APP_BIN"
    fi

    if [ ! -x "$PREVIEW_BIN" ]; then
        log "ERROR: missing executable for preview"
        persist_log
        show_message "BootAnim Manager" "Preview failed: missing bootanim executable.\n\nLog: $PERSIST_LOG"
        exit 0
    fi

    log "preview binary: $PREVIEW_BIN"
    log "preview animation: $PREVIEW_ANIM"
    log "preview seconds: $PREVIEW_SECONDS"
    persist_log

    clear 2>/dev/null
    echo "BootAnim preview starting..."
    echo "It will return automatically after $PREVIEW_SECONDS seconds."
    sleep 1

    "$PREVIEW_BIN" \
        "$PREVIEW_ANIM" \
        --fb /dev/fb0 \
        --scale "$SCALE" \
        --loop-start "$LOOP_START" \
        --max-seconds "$PREVIEW_SECONDS" \
        --wait-fb \
        --wait-fb-ms "$WAIT_FB_MS" \
        >> "$LOG_FILE" 2>&1

    persist_log
    show_message "BootAnim Manager" "Preview finished.\n\nIf nothing appeared, the muOS menu may still be drawing over fb0.\n\nLog: $PERSIST_LOG"
}

case "$1" in
    install)
        install_bootanim
        ;;
    uninstall)
        uninstall_bootanim
        ;;
    preview)
        preview_bootanim
        ;;
    menu|*)
        log "no action specified; use install, uninstall, or preview"
        persist_log
        exit 0
        ;;
esac

exit 0
