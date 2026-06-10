# banim

**banim** is a tiny boot-animation system for Linux handhelds.

It was built for devices where a normal video decoder is too heavy or starts too late during boot. Instead of playing MP4 directly on the device, `banim` uses a prepacked framebuffer-friendly animation format: **BNF1 / `.banim`**.

The goal is simple:

- convert frames or MP4 on a PC;
- copy one `bootanim.banim` file to the handheld;
- start a tiny framebuffer player early in boot;
- stop automatically when the real frontend takes over `/dev/fb0`.

The tested targets in this repository are:

- **Knulli / Batocera-style systems** using `/boot/boot-custom.sh`;
- **muOS / MustardOS** using a reliable 3-entry app package.

---

## Preview examples

Example animations are included in [`animation_examples/`](animation_examples/). To use one, copy or rename it to `bootanim.banim`.

### 360×240, 30 FPS, loop from frame 90

![30 FPS preview](animation_examples/previews/example_360x240_30fps_loop90_preview.gif)

Video file: [`example_360x240_30fps_loop90_preview.mp4`](animation_examples/previews/example_360x240_30fps_loop90_preview.mp4)

### 360×240, 60 FPS, loop from frame 180

![60 FPS preview](animation_examples/previews/example_360x240_60fps_loop180_preview.gif)

Video file: [`example_360x240_60fps_loop180_preview.mp4`](animation_examples/previews/example_360x240_60fps_loop180_preview.mp4)

---

## How it works

### 1. Prepare the animation on a PC

The Python tool in [`tools/banim_pack/`](tools/banim_pack/) converts an MP4 or a ZIP/folder of frames into a `.banim` file.

Example from MP4:

```sh
python3 tools/banim_pack/banim_pack.py animation.mp4 bootanim.banim \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180 \
  --report bootanim_report.json \
  --contact-sheet contact_sheet.jpg
```

Example from frames:

```sh
python3 tools/banim_pack/banim_pack.py frames.zip bootanim.banim \
  --fps 60 \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180
```

If the source is an MP4, the tool reads the framerate from the video. If the source is a folder or ZIP of frames, pass `--fps` manually.

### 2. Play the animation during boot

The framebuffer player is a very small AArch64 Linux binary. It opens `/dev/fb0`, decodes the `.banim` file, writes RGB565 pixels directly to the framebuffer, and can stop automatically when another process opens the framebuffer.

The important runtime option is:

```sh
--stop-on-any-fb-owner
```

That makes the player portable across frontends. It does not need to know whether the next UI process is EmulationStation, muxfrontend, Pegasus, MinUI, or something else. When another process opens `/dev/fb0`, `bootanim` exits and lets the frontend take over.

---

## File format summary

`.banim` files use the `BNF1` format:

- little-endian header;
- logical frame size, output size, FPS, frame count, loop range;
- per-frame index table;
- dirty rectangles;
- RGB565 run-length encoding.

It is designed for early boot:

- no MP4/H.264 decoder on the handheld;
- no dynamic image libraries;
- very small runtime player;
- simple sequential decode;
- good compression for boot animations with limited movement.

---

## Repository layout

```text
banim/
├── README.md
├── animation_examples/
│   ├── README.md
│   ├── example_360x240_30fps_loop90.banim
│   ├── example_360x240_60fps_loop180.banim
│   └── previews/
│       ├── *.gif
│       ├── *.mp4
│       └── *_first_frame.png
├── knulli/
│   ├── README.md
│   ├── boot-custom.sh
│   └── bootanim/
│       ├── bootanim
│       ├── bootanim_v5_nolibc.c
│       └── start_aarch64.S
├── muos/
│   ├── README.md
│   └── reliable_three_apps/
└── tools/
    └── banim_pack/
```

---

## Knulli quick install

Knulli does not need a manager app. Copy the hook script to the boot partition, and place the player + animation under `/boot/bootanim`.

Expected paths on the device:

```text
/boot/boot-custom.sh
/boot/bootanim/bootanim
/boot/bootanim/bootanim.banim
```

Typical install:

```sh
mount -o remount,rw /boot

mkdir -p /boot/bootanim
cp knulli/boot-custom.sh /boot/boot-custom.sh
cp knulli/bootanim/bootanim /boot/bootanim/bootanim
cp bootanim.banim /boot/bootanim/bootanim.banim

chmod +x /boot/boot-custom.sh
chmod +x /boot/bootanim/bootanim

sync
mount -o remount,ro /boot
```

Then reboot and inspect:

```sh
cat /tmp/bootanim.log
```

Configuration is inside `knulli/boot-custom.sh`. For example, if your `.banim` is `320x240` and the screen is `640x480`, use:

```sh
--scale 2
```

---

## muOS reliable install

The reliable muOS package is the 3-entry app version:

- **BootAnim Install**
- **BootAnim Uninstall**
- **BootAnim Preview**

This version was kept because it works reliably with muOS. Experimental single-menu versions are intentionally not included in this release.

Copy the `.muxapp` from:

```text
muos/reliable_three_apps/BanimManager_reliable_three_apps.muxapp
```

to:

```text
/mnt/mmc/ARCHIVE
```

Then install it using muOS Archive Manager.

Put your animation here:

```text
/mnt/mmc/MUOS/bootanim/bootanim.banim
```

After running **BootAnim Install**, the boot hook is installed at:

```text
/opt/muos/script/init/S03bootanim
```

The runtime files are copied to:

```text
/opt/bootanim/
```

Logs:

```sh
cat /mnt/mmc/MUOS/bootanim-manager-last.log
cat /tmp/bootanim.log
```

---

## Boot logo notes

The boot animation player starts once Linux userspace is running and `/dev/fb0` exists. It does not replace the bootloader itself.

For the smoothest visual transition, set the static boot logo to the first frame of the animation. The Python tool can export static logos from the final `.banim` frame 0, optionally resized:

```sh
python3 tools/banim_pack/banim_pack.py animation.mp4 bootanim.banim \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180 \
  --export-knulli-bootlogo bootlogo.bmp \
  --export-muos-logo muoslogo.ico \
  --logo-size 640x480
```

---

## Safety / recovery

### Knulli

Disable the animation by removing or renaming:

```text
/boot/boot-custom.sh
```

or remove:

```text
/boot/bootanim/bootanim.banim
```

### muOS

Disable boot animation from SSH:

```sh
rm -f /opt/muos/script/init/S03bootanim
rm -rf /opt/bootanim
sync
reboot
```

If the app package was installed:

```sh
rm -rf /mnt/mmc/MUOS/application/bootanim_install
rm -rf /mnt/mmc/MUOS/application/bootanim_uninstall
rm -rf /mnt/mmc/MUOS/application/bootanim_preview
rm -rf /mnt/mmc/MUOS/application/bootanim_common
sync
```

---

## Status

Validated:

- BNF1 `.banim` conversion from frames and MP4;
- 30 FPS and 60 FPS examples;
- Knulli early boot via `/boot/boot-custom.sh`;
- portable stop-on-any-fb-owner handoff;
- muOS reliable 3-entry package.

Experimental / not included:

- single-entry muOS visual manager;
- DRM/KMS renderer;
- U-Boot-level animation.

---

## License

Add your preferred license before publishing. If you want a permissive default, MIT is a good fit for this project.
