BootAnim Manager v6 for muOS

This package exposes three muOS application entries instead of an in-app shell menu:
- BootAnim Install
- BootAnim Uninstall
- BootAnim Preview

Reason: muOS application launchers do not provide a normal interactive terminal, so echo/read/dialog style shell menus are not reliably visible from the frontend.

Place your animation at:
/mnt/mmc/MUOS/bootanim/bootanim.banim

Logs:
/mnt/mmc/MUOS/bootanim-manager-last.log
/tmp/bootanim.log
