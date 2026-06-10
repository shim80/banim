# Animation examples

This folder contains example boot animations in `.banim` format.

To use an example on a handheld, copy or rename it to:

```text
bootanim.banim
```

For Knulli, place it at:

```text
/boot/bootanim/bootanim.banim
```

For muOS, place it at:

```text
/mnt/mmc/MUOS/bootanim/bootanim.banim
```

## Included examples

| File | Logical size | FPS | Loop start | Preview |
|---|---:|---:|---:|---|
| `example_360x240_30fps_loop90.banim` | 360×240 | 30 | frame 90 | [MP4](previews/example_360x240_30fps_loop90_preview.mp4) |
| `example_360x240_60fps_loop180.banim` | 360×240 | 60 | frame 180 | [MP4](previews/example_360x240_60fps_loop180_preview.mp4) |

## Inline previews

### 30 FPS example

![30 FPS preview](previews/example_360x240_30fps_loop90_preview.gif)

### 60 FPS example

![60 FPS preview](previews/example_360x240_60fps_loop180_preview.gif)

## Notes

The examples are stored at `360x240`. Use the player scale option to match the device screen:

- `--scale 1` for a 360×240 output;
- `--scale 2` for a 720×480 output.

If your handheld is `640x480`, create a `320x240` animation and play it with `--scale 2`.
