banim_pack.py v5 - frames/video to BNF1 .banim + logo export from .banim

Main change in v5:
  Logo files can be generated from the encoded .banim frame 0, then resized.
  This makes bootanim.banim the single source of truth.

Dependencies:
  python3 -m pip install pillow numpy
  ffmpeg/ffprobe required only for video input.

Examples:

1) 640x480 source -> 320x240 .banim -> 640x480 bootlogo.bmp from .banim frame 0:

  python3 banim_pack.py animation.mp4 bootanim.banim \
    --logical-size 320x240 \
    --resize lanczos \
    --loop-start 180 \
    --export-knulli-bootlogo bootlogo.bmp \
    --logo-source banim \
    --logo-size 640x480 \
    --report bootanim_report.json \
    --contact-sheet contact_sheet.jpg

2) Same from frames:

  python3 banim_pack.py frames.zip bootanim.banim \
    --fps 60 \
    --logical-size 320x240 \
    --resize lanczos \
    --loop-start 180 \
    --export-knulli-bootlogo bootlogo.bmp \
    --export-muos-logo muoslogo.ico \
    --logo-source banim \
    --logo-size 640x480

Logo options:
  --logo-source banim   Use frame 0 decoded from the final .banim. Default.
  --logo-source source  Use the original source first frame before .banim resize.
  --logo-size WxH       Resize exported logo image.
  --logo-resize lanczos Resize method. Use nearest for pixel art.

Note:
  The .banim can be 320x240 while the exported bootlogo.bmp is 640x480.
  For playback on a 640x480 screen, run bootanim with --scale 2.
