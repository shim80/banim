# banim_pack.py

`banim_pack.py` converts videos or frame sequences into `bootanim.banim`.

## Requirements

```sh
python3 -m pip install pillow numpy
```

For MP4/MOV/MKV input, install `ffmpeg` and `ffprobe`.

## Convert MP4

```sh
python3 banim_pack.py animation.mp4 bootanim.banim \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180 \
  --report bootanim_report.json \
  --contact-sheet contact_sheet.jpg
```

The FPS is read from the video automatically.

## Convert frames

```sh
python3 banim_pack.py frames.zip bootanim.banim \
  --fps 60 \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180
```

Frames are sorted naturally, so names like `boot_0001.bmp`, `boot_0002.bmp`, etc. work correctly.

## Resolution behavior

If `--logical-size` is omitted, the tool uses the first frame size.

If `--logical-size` is provided and differs from the source, pass a resize filter:

```sh
--resize lanczos
```

Typical handheld workflow:

```text
source video:       640x480
banim logical size: 320x240
player scale:       2
final output:       640x480
```

## Export boot logos

The tool can export static boot logos from frame 0 of the final `.banim` and resize them:

```sh
python3 banim_pack.py animation.mp4 bootanim.banim \
  --logical-size 320x240 \
  --resize lanczos \
  --loop-start 180 \
  --export-knulli-bootlogo bootlogo.bmp \
  --export-muos-logo muoslogo.ico \
  --logo-size 640x480
```

## Useful options

```text
--fps 60                         FPS for frame/ZIP input
--loop-start 180                 human frame number where looping begins
--logical-size 320x240           output size stored inside .banim
--resize nearest|bilinear|bicubic|lanczos
--report bootanim_report.json
--contact-sheet contact_sheet.jpg
--export-first-frame first_frame.png
--export-knulli-bootlogo bootlogo.bmp
--export-muos-logo muoslogo.ico
--logo-size 640x480
```
