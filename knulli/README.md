# Knulli / Batocera-style setup

Knulli only needs a boot hook script plus the framebuffer player.

Expected device paths:

```text
/boot/boot-custom.sh
/boot/bootanim/bootanim
/boot/bootanim/bootanim.banim
```

## Install

Copy your `bootanim.banim` next to this folder or adapt the path in the command below.

```sh
mount -o remount,rw /boot

mkdir -p /boot/bootanim
cp boot-custom.sh /boot/boot-custom.sh
cp bootanim/bootanim /boot/bootanim/bootanim
cp bootanim.banim /boot/bootanim/bootanim.banim

chmod +x /boot/boot-custom.sh
chmod +x /boot/bootanim/bootanim

sync
mount -o remount,ro /boot
```

Reboot and check:

```sh
cat /tmp/bootanim.log
```

## Configuration

Edit `boot-custom.sh` before copying it to the device.

Important options:

```sh
--scale 2
--loop-start 180
--max-seconds 120
--stop-on-any-fb-owner
```

Use `--scale 2` when the `.banim` logical size is half the screen size, for example `320x240` on a `640x480` screen.

## Disable

```sh
mount -o remount,rw /boot
rm -f /boot/boot-custom.sh
sync
mount -o remount,ro /boot
```
