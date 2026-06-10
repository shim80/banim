# muOS setup

The reliable muOS version is the 3-entry package:

- **BootAnim Install**
- **BootAnim Uninstall**
- **BootAnim Preview**

This approach is intentionally simple and reliable. Experimental single-menu prototypes were not kept in this release because input handling differed across muOS contexts.

## Install package

Copy this file to the muOS archive folder:

```text
reliable_three_apps/BanimManager_reliable_three_apps.muxapp
```

Destination on the device:

```text
/mnt/mmc/ARCHIVE
```

Install it from muOS Archive Manager.

## Add animation

Place your animation here:

```sh
mkdir -p /mnt/mmc/MUOS/bootanim
cp bootanim.banim /mnt/mmc/MUOS/bootanim/bootanim.banim
sync
```

Then run:

```text
Applications → BootAnim Install
```

## Preview

Run:

```text
Applications → BootAnim Preview
```

## Uninstall

Run:

```text
Applications → BootAnim Uninstall
```

Or from SSH:

```sh
rm -f /opt/muos/script/init/S03bootanim
rm -rf /opt/bootanim
sync
reboot
```

## Logs

```sh
cat /mnt/mmc/MUOS/bootanim-manager-last.log
cat /tmp/bootanim.log
```
