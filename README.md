# banim

**banim** is a tiny boot animation system for Linux handheld consoles.

It is designed for devices where the normal boot logo is static, but the user wants a lightweight animated handoff before the frontend takes over.

The project includes:

- a compact `.banim` animation format
- a direct framebuffer player
- a Python packing tool for MP4 videos or image frames
- a working Knulli / Batocera boot hook
- a reliable muOS installer app
- ready-to-use animation examples

---

## Demo boot animations : 

The example animations are available in `animation_examples/`.

### GBA



https://github.com/user-attachments/assets/74fb67aa-87ab-4f93-8e47-9f6cdbc2c393



### Knulli



https://github.com/user-attachments/assets/aa9148bc-3580-42fd-903e-711908804ccf



### muOS



https://github.com/user-attachments/assets/39e1d9e1-264f-4ddb-be71-7a34014b097a


---

## How it works

Most handheld Linux systems show a static boot image first, then later start the main frontend.

`banim` starts a tiny framebuffer player early in the boot process:

    boot logo
    -> Linux starts
    -> banim player opens /dev/fb0
    -> animation plays
    -> frontend opens /dev/fb0
    -> banim stops and lets the frontend take over

The player does not use a heavy video decoder at boot. Instead, it plays a pre-packed `.banim` file.

---

## The `.banim` format

The current format is called `BNF1`.

It stores:

- animation width and height
- output size metadata
- FPS
- frame count
- loop start frame
- RGB565 frame data
- dirty rectangles
- simple RLE compression

The goal is to keep boot playback very small and deterministic:

    no ffmpeg at boot
    no mpv at boot
    no PNG/JPEG decoder at boot
    no SDL requirement for playback
    direct /dev/fb0 rendering

---

## Animation structure

A boot animation normally has two parts:

    startup segment
    -> frames that play once

    loop segment
    -> frames that repeat until the frontend is ready

Example:

    260 total frames
    loop start = 180

That means:

    frames 1-179   play once
    frames 180-260 loop

When using the packer, pass the human frame number:

    --loop-start 180

---

## Resolution and scaling

You can encode the `.banim` at a smaller logical resolution and scale it at playback.

Example for a `640x480` screen:

    source frames: 640x480
    .banim file:   320x240
    player scale:  2
    final output:  640x480

This keeps the `.banim` smaller while still filling the screen.

To create a `320x240` `.banim` from `640x480` frames:

    python3 tools/banim_pack/banim_pack.py frames.zip bootanim.banim \
      --fps 60 \
      --logical-size 320x240 \
      --resize lanczos \
      --loop-start 180 \
      --report bootanim_report.json \
      --contact-sheet contact_sheet.jpg

Then run the player with:

    --scale 2

---

## Creating `.banim` files

The packer is located here:

    tools/banim_pack/banim_pack.py

Install dependencies on your PC:

    python3 -m pip install pillow numpy

For MP4 input, install `ffmpeg` and `ffprobe`.

On macOS:

    brew install ffmpeg

---

## Convert frames to `.banim`

    python3 tools/banim_pack/banim_pack.py frames.zip bootanim.banim \
      --fps 60 \
      --loop-start 180 \
      --report bootanim_report.json \
      --contact-sheet contact_sheet.jpg

You can also pass a folder instead of a ZIP:

    python3 tools/banim_pack/banim_pack.py frames/ bootanim.banim \
      --fps 60 \
      --loop-start 180

---

## Convert MP4 to `.banim`

For video input, the FPS is read automatically from the MP4:

    python3 tools/banim_pack/banim_pack.py animation.mp4 bootanim.banim \
      --loop-start 180 \
      --report bootanim_report.json \
      --contact-sheet contact_sheet.jpg

To resize while packing:

    python3 tools/banim_pack/banim_pack.py animation.mp4 bootanim.banim \
      --logical-size 320x240 \
      --resize lanczos \
      --loop-start 180

---

## `banim_pack.py` options

### Positional arguments

`input`

Input file or folder.

Supported inputs:

- `.zip` containing frames
- folder containing frames
- video file such as `.mp4`, `.mov`, `.mkv`

`output`

Output `.banim` file.

Example:

    python3 tools/banim_pack/banim_pack.py input.mp4 bootanim.banim

### Timing options

`--fps FPS`

Sets animation FPS.

Required for image frames. Optional for videos, because video FPS is read with `ffprobe`.

`--loop-start FRAME`

Human frame number where the loop starts.

Example:

    --loop-start 180

means frame 180 is the first frame of the loop.

### Size options

`--logical-size WIDTHxHEIGHT`

Sets the encoded `.banim` resolution.

Example:

    --logical-size 320x240

`--resize METHOD`

Resize method used when source size differs from logical size.

Common value:

    --resize lanczos

### Report and preview options

`--report FILE.json`

Writes a JSON report.

`--contact-sheet FILE.jpg`

Creates a contact sheet preview.

### Logo export options

`--export-first-frame FILE.png`

Exports frame 0 as PNG.

`--export-knulli-bootlogo bootlogo.bmp`

Exports a BMP boot logo.

`--export-muos-logo muoslogo.ico`

Exports an ICO logo.

`--logo-source banim`

Exports logos from the final `.banim` frame 0.

`--logo-size WIDTHxHEIGHT`

Resizes the exported logo.

Example:

    python3 tools/banim_pack/banim_pack.py animation.mp4 bootanim.banim \
      --logical-size 320x240 \
      --resize lanczos \
      --loop-start 180 \
      --export-knulli-bootlogo bootlogo.bmp \
      --logo-size 640x480

---

## Knulli / Batocera installation

Knulli uses the normal Batocera early boot hook:

    /boot/boot-custom.sh

The Knulli folder contains:

    knulli/
    ├── boot-custom.sh
    └── bootanim/
        └── bootanim

Copy the files to the boot partition:

    mount -o remount,rw /boot

    mkdir -p /boot/bootanim

    cp knulli/boot-custom.sh /boot/boot-custom.sh
    cp knulli/bootanim/bootanim /boot/bootanim/bootanim
    cp bootanim.banim /boot/bootanim/bootanim.banim

    chmod +x /boot/boot-custom.sh
    chmod +x /boot/bootanim/bootanim

    sync
    mount -o remount,ro /boot

The Knulli hook runs:

    /boot/bootanim/bootanim.banim

The player starts when `/dev/fb0` appears and stops when another process opens `/dev/fb0`.

---

## muOS installation

The reliable muOS version uses three app entries:

    BootAnim Install
    BootAnim Uninstall
    BootAnim Preview

This version is intentionally kept simple and reliable (mostly because I don't know how  to code SDL app...)

The muOS package is in:

    muos/reliable_three_apps/

Copy the `.muxapp` to:

    /mnt/mmc/ARCHIVE

Then install it from the muOS Archive Manager.

Place your animation here:

    /mnt/mmc/MUOS/bootanim/bootanim.banim

The installer creates:

    /opt/bootanim/bootanim
    /opt/bootanim/bootanim.banim
    /opt/muos/script/init/S03bootanim

The boot hook starts the animation early and stops when another process takes `/dev/fb0`.

---

## Animation examples

Example `.banim` files are in:

    animation_examples/

To use an example, copy or rename it to:

    bootanim.banim

Examples:

    cp animation_examples/gba.banim bootanim.banim
    cp animation_examples/knulli.banim bootanim.banim
    cp animation_examples/muos.banim bootanim.banim

---

## Recovery

### Knulli

Disable the boot animation:

    mount -o remount,rw /boot
    rm -f /boot/boot-custom.sh
    sync
    mount -o remount,ro /boot
    reboot

### muOS

Disable the boot animation:

    rm -f /opt/muos/script/init/S03bootanim
    rm -rf /opt/bootanim
    sync
    reboot
    or use uninstall app

---

## Project status

Validated:

- Knulli / Batocera framebuffer boot animation
- muOS reliable three-app installer
- `.banim` generation from frames
- `.banim` generation from MP4
- 320x240 logical animations scaled to 640x480
- 360x240 logical animations scaled to 720x480

Experimental / not included as reliable:

- single-entry muOS graphical manager
- SDL2 muOS manager
- DRM/KMS renderer

