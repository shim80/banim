#!/usr/bin/env python3
"""
banim_pack.py - Convert frames or MP4/video into a BNF1 .banim boot animation.

BNF1 is the simple format used by the current Knulli/Batocera framebuffer player:
  - RGB565 pixels
  - dirty rectangles per frame
  - RLE packets: count:u8 + color_rgb565:u16le
  - logical frame size auto-detected by default, or forced with --logical-size
  - optional logo export from source frame or from encoded .banim frame 0

Inputs:
  - frame directory
  - .zip containing frames
  - video file, e.g. .mp4/.mov/.mkv/.webm

Examples:
  python3 banim_pack.py frames.zip bootanim.banim --fps 60 --loop-start 180
  python3 banim_pack.py frames/ bootanim.banim --fps 30 --loop-start 90
  python3 banim_pack.py boot.mp4 bootanim.banim --loop-start 180
  python3 banim_pack.py boot.mp4 bootanim.banim --loop-start 180 --logical-size 360x240 --resize lanczos

Requires:
  Python 3 + Pillow + numpy
  For video input: ffmpeg + ffprobe available in PATH
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from fractions import Fraction
from pathlib import Path
from typing import List, Sequence, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit("Missing dependency: Pillow. Install with: python3 -m pip install pillow") from exc

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit("Missing dependency: numpy. Install with: python3 -m pip install numpy") from exc

Rect = Tuple[int, int, int, int]

SUPPORTED_FRAME_EXTS = {".bmp", ".png", ".ppm", ".jpg", ".jpeg"}
SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def natural_key(path: Path) -> List[object]:
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Missing external tool: {name}. Install ffmpeg/ffprobe or use a frame directory/zip instead.")
    return path


def parse_rate(rate: str) -> float:
    rate = rate.strip()
    if not rate or rate == "0/0":
        return 0.0
    try:
        return float(Fraction(rate))
    except Exception:
        try:
            return float(rate)
        except Exception:
            return 0.0


def probe_video_fps(video_path: Path) -> Tuple[int, float, str]:
    """Return (integer fps for BNF1, exact fps float, raw rate string)."""
    ffprobe = require_tool("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate,r_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"ffprobe failed for {video_path}:\n{exc.stderr}") from exc

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or []
    if not streams:
        raise SystemExit(f"No video stream found in: {video_path}")

    stream = streams[0]
    raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/0"
    fps_exact = parse_rate(raw)
    if fps_exact <= 0:
        raw = stream.get("r_frame_rate") or "0/0"
        fps_exact = parse_rate(raw)

    if fps_exact <= 0:
        raise SystemExit(f"Could not determine FPS from video: {video_path}")

    fps_int = int(round(fps_exact))
    if fps_int < 1:
        fps_int = 1
    if fps_int > 240:
        raise SystemExit(f"Detected FPS is too high for BNF1 header: {fps_exact:.3f}")

    return fps_int, fps_exact, raw


def extract_video_frames(video_path: Path, work_dir: Path | None = None) -> Path:
    ffmpeg = require_tool("ffmpeg")
    extracted_dir = Path(tempfile.mkdtemp(prefix="banim_video_frames_", dir=str(work_dir) if work_dir else None))
    out_pattern = str(extracted_dir / "frame_%06d.png")

    # -vsync 0 preserves decoded frames instead of duplicating/dropping to a target CFR.
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-map", "0:v:0",
        "-vsync", "0",
        out_pattern,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        raise SystemExit(f"ffmpeg frame extraction failed for {video_path}:\n{exc.stderr}") from exc

    return extracted_dir


def collect_frames(input_path: Path, work_dir: Path | None = None) -> Tuple[List[Path], Path | None, dict]:
    """Return sorted frame paths, optional temp dir, metadata."""
    extracted_dir: Path | None = None
    meta: dict = {"input_type": "frames", "detected_fps": None, "detected_fps_exact": None, "detected_fps_raw": None}

    suffix = input_path.suffix.lower()

    if input_path.is_file() and suffix == ".zip":
        extracted_dir = Path(tempfile.mkdtemp(prefix="banim_frames_", dir=str(work_dir) if work_dir else None))
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(extracted_dir)
        root = extracted_dir
    elif input_path.is_file() and suffix in SUPPORTED_VIDEO_EXTS:
        fps_int, fps_exact, raw = probe_video_fps(input_path)
        extracted_dir = extract_video_frames(input_path, work_dir=work_dir)
        root = extracted_dir
        meta = {"input_type": "video", "detected_fps": fps_int, "detected_fps_exact": fps_exact, "detected_fps_raw": raw}
    elif input_path.is_dir():
        root = input_path
    else:
        raise SystemExit(f"Input is not a frame directory, zip, or supported video file: {input_path}")

    frames = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_FRAME_EXTS]
    frames.sort(key=natural_key)

    if not frames:
        raise SystemExit(f"No frames found in: {input_path}")

    return frames, extracted_dir, meta


def rgb888_to_rgb565(arr: np.ndarray) -> np.ndarray:
    r = arr[:, :, 0].astype(np.uint16)
    g = arr[:, :, 1].astype(np.uint16)
    b = arr[:, :, 2].astype(np.uint16)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def encode_rle_rgb565(flat: np.ndarray) -> bytes:
    """Encode a flat uint16 RGB565 array as count:u8 + color:u16le."""
    out = bytearray()
    n = int(flat.size)
    i = 0

    while i < n:
        color = int(flat[i])
        j = i + 1
        while j < n and (j - i) < 255 and int(flat[j]) == color:
            j += 1
        out.append(j - i)
        out += struct.pack("<H", color)
        i = j

    return bytes(out)


def one_dirty_bbox(mask: np.ndarray) -> List[Rect]:
    if not mask.any():
        return []
    ys, xs = np.where(mask)
    x0 = int(xs.min())
    x1 = int(xs.max())
    y0 = int(ys.min())
    y1 = int(ys.max())
    return [(x0, y0, x1 - x0 + 1, y1 - y0 + 1)]


def row_group_dirty_rects(mask: np.ndarray, merge_factor: float = 1.15) -> List[Rect]:
    """
    Split changes into runs of changed rows, each with its own x bbox.
    This keeps decoding simple while usually saving more than one huge bbox.
    """
    if not mask.any():
        return []

    row_has = mask.any(axis=1)
    rects: List[Rect] = []
    y = 0
    height = int(mask.shape[0])

    while y < height:
        if not row_has[y]:
            y += 1
            continue

        y0 = y
        while y < height and row_has[y]:
            y += 1
        y1 = y - 1

        sub = mask[y0 : y1 + 1, :]
        xs = np.flatnonzero(sub.any(axis=0))
        if xs.size:
            x0 = int(xs[0])
            x1 = int(xs[-1])
            rects.append((x0, y0, x1 - x0 + 1, y1 - y0 + 1))

    # Merge adjacent row groups when the combined bbox is not too wasteful.
    merged: List[List[int]] = []
    for x, y, w, h in rects:
        if not merged:
            merged.append([x, y, w, h])
            continue

        px, py, pw, ph = merged[-1]
        left = min(px, x)
        right = max(px + pw - 1, x + w - 1)
        top = min(py, y)
        bottom = max(py + ph - 1, y + h - 1)
        combined_area = (right - left + 1) * (bottom - top + 1)
        separate_area = pw * ph + w * h

        if combined_area <= separate_area * merge_factor:
            merged[-1] = [left, top, right - left + 1, bottom - top + 1]
        else:
            merged.append([x, y, w, h])

    return [tuple(r) for r in merged]


def image_size(path: Path) -> Tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def load_source_frame_rgb(path: Path) -> Image.Image:
    """Load the first source frame before any BNF1 resize/downscale."""
    return Image.open(path).convert("RGB")


def save_bootlogo_bmp_from_image(im: Image.Image, output: Path) -> None:
    """Save a plain Windows BMP from the original first frame.

    Knulli/Batocera bootlogo.bmp usually accepts standard BMP. This intentionally
    uses the source frame size, not the BNF1 logical size, so a 640x480 source can
    produce a 640x480 boot logo even if the .banim is downscaled to 320x240.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(output, format="BMP")


def save_muos_ico_from_image(im: Image.Image, output: Path, sizes: Sequence[int]) -> None:
    """Save a valid Windows ICO from the first frame.

    ICO files are icon containers, not framebuffer images. To keep the full frame
    visible, the image is letterboxed into square icon canvases. Standard ICO
    dimensions are limited to 256x256 for best compatibility.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    rgba = im.convert("RGBA")
    ico_images = []
    for size in sizes:
        if size < 16 or size > 256:
            raise SystemExit("ICO sizes must be between 16 and 256")
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        tmp = rgba.copy()
        tmp.thumbnail((size, size), Image.Resampling.LANCZOS)
        x = (size - tmp.size[0]) // 2
        y = (size - tmp.size[1]) // 2
        canvas.paste(tmp, (x, y), tmp)
        ico_images.append(canvas)
    # Pillow uses the provided sizes to encode multiple entries from one image.
    ico_images[-1].save(output, format="ICO", sizes=[(s, s) for s in sizes])


def parse_ico_sizes(s: str) -> List[int]:
    try:
        values = [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated sizes, e.g. 64,128,256") from exc
    if not values:
        raise argparse.ArgumentTypeError("expected at least one ICO size")
    for v in values:
        if v < 16 or v > 256:
            raise argparse.ArgumentTypeError("ICO sizes must be between 16 and 256")
    return values


def load_frame_rgb565(path: Path, logical_size: Tuple[int, int], resize_mode: str) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    target_w, target_h = logical_size

    if im.size != logical_size:
        if resize_mode == "none":
            raise SystemExit(f"Frame has size {im.size}, expected {logical_size}: {path}")
        resample = Image.Resampling.NEAREST if resize_mode == "nearest" else Image.Resampling.LANCZOS
        im = im.resize((target_w, target_h), resample)

    arr = np.asarray(im, dtype=np.uint8)
    return rgb888_to_rgb565(arr)


def encode_frames(
    frames: Sequence[Path],
    logical_size: Tuple[int, int],
    resize_mode: str,
    rect_mode: str,
    merge_factor: float,
) -> Tuple[List[bytes], dict]:
    frame_blobs: List[bytes] = []
    payload_sizes: List[int] = []
    full_rle_total = 0
    frames_no_change = 0
    prev: np.ndarray | None = None
    first_frame: np.ndarray | None = None
    last_frame: np.ndarray | None = None

    for index, path in enumerate(frames):
        frame = load_frame_rgb565(path, logical_size, resize_mode)
        if index == 0:
            first_frame = frame.copy()

        full_rle_total += len(encode_rle_rgb565(frame.reshape(-1)))

        if index == 0:
            rects: List[Rect] = [(0, 0, logical_size[0], logical_size[1])]
        else:
            assert prev is not None
            diff = frame != prev
            if not diff.any():
                rects = []
                frames_no_change += 1
            elif rect_mode == "bbox":
                rects = one_dirty_bbox(diff)
            elif rect_mode == "rows":
                rects = row_group_dirty_rects(diff, merge_factor=merge_factor)
            else:
                raise SystemExit(f"Unknown rect mode: {rect_mode}")

        blob = bytearray(struct.pack("<HH", len(rects), 0))
        for x, y, w, h in rects:
            sub = frame[y : y + h, x : x + w].reshape(-1)
            rle = encode_rle_rgb565(sub)
            blob += struct.pack("<HHHHI", x, y, w, h, len(rle))
            blob += rle

        frame_blobs.append(bytes(blob))
        payload_sizes.append(len(blob))
        prev = frame
        last_frame = frame

    stats = {
        "full_frame_rgb565_rle_bytes_estimate": int(full_rle_total),
        "frames_with_no_change": int(frames_no_change),
        "min_frame_payload": int(min(payload_sizes)),
        "max_frame_payload": int(max(payload_sizes)),
        "avg_frame_payload": float(sum(payload_sizes) / len(payload_sizes)),
        "first_frame": first_frame,
        "last_frame": last_frame,
    }
    return frame_blobs, stats






def resize_rgb_image(im: Image.Image, size: tuple[int, int], resize_mode: str) -> Image.Image:
    if resize_mode == "none" and im.size != size:
        raise SystemExit(f"Logo source has size {im.size}, expected {size}; use --logo-resize nearest or lanczos")
    if resize_mode == "nearest":
        resample = Image.Resampling.NEAREST
    else:
        resample = Image.Resampling.LANCZOS
    return im.resize(size, resample)


def rgb565_to_rgb888_image(rgb565: np.ndarray) -> Image.Image:
    arr = np.empty((rgb565.shape[0], rgb565.shape[1], 3), dtype=np.uint8)
    r5 = (rgb565 >> 11) & 0x1F
    g6 = (rgb565 >> 5) & 0x3F
    b5 = rgb565 & 0x1F
    arr[:, :, 0] = ((r5 * 255 + 15) // 31).astype(np.uint8)
    arr[:, :, 1] = ((g6 * 255 + 31) // 63).astype(np.uint8)
    arr[:, :, 2] = ((b5 * 255 + 15) // 31).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def decode_bnf1_first_frame(path: Path) -> Image.Image:
    data = path.read_bytes()
    if len(data) < 64 or data[:4] != b"BNF1":
        raise SystemExit(f"Not a BNF1 file: {path}")
    width, height = struct.unpack_from("<HH", data, 8)
    index_offset = struct.unpack_from("<I", data, 28)[0]
    if index_offset + 8 > len(data):
        raise SystemExit("Invalid BNF1 index offset")
    frame_offset, frame_size = struct.unpack_from("<II", data, index_offset)
    if frame_offset + frame_size > len(data):
        raise SystemExit("Invalid BNF1 first-frame offset/size")
    canvas = np.zeros((height, width), dtype=np.uint16)
    p0 = frame_offset
    end = frame_offset + frame_size
    if p0 + 4 > end:
        raise SystemExit("Invalid first frame")
    rect_count, _flags = struct.unpack_from("<HH", data, p0)
    p0 += 4
    for _ in range(rect_count):
        if p0 + 12 > end:
            raise SystemExit("Invalid rect header in first frame")
        x, y, w, h, rle_size = struct.unpack_from("<HHHHI", data, p0)
        p0 += 12
        rle_end = p0 + rle_size
        if rle_end > end or x + w > width or y + h > height:
            raise SystemExit("Invalid rect bounds/RLE size in first frame")
        total = w * h
        flat = np.empty(total, dtype=np.uint16)
        pos = 0
        while p0 < rle_end and pos < total:
            count = data[p0]
            color = struct.unpack_from("<H", data, p0 + 1)[0]
            p0 += 3
            n = min(count, total - pos)
            flat[pos:pos+n] = color
            pos += n
        if pos != total:
            raise SystemExit("Short RLE data in first frame")
        canvas[y:y+h, x:x+w] = flat.reshape((h, w))
        p0 = rle_end
    return rgb565_to_rgb888_image(canvas)


def prepare_logo_image_from_banim(path: Path, size: tuple[int, int] | None, resize_method: str) -> Image.Image:
    img = decode_bnf1_first_frame(path)
    if size is not None and img.size != size:
        img = resize_rgb_image(img, size, resize_method)
    return img


def build_bnf1(
    frame_blobs: Sequence[bytes],
    output_path: Path,
    logical_size: Tuple[int, int],
    output_size: Tuple[int, int],
    fps: int,
    loop_start_1based: int,
) -> int:
    frame_count = len(frame_blobs)
    loop_start_zero = max(0, min(frame_count - 1, loop_start_1based - 1))
    loop_end_zero = frame_count - 1

    header_size = 64
    index_offset = header_size
    index_size = frame_count * 8
    data_offset = index_offset + index_size

    # IMPORTANT: the current player expects absolute file offsets in the frame index.
    offsets: List[Tuple[int, int]] = []
    current = data_offset
    for blob in frame_blobs:
        offsets.append((current, len(blob)))
        current += len(blob)

    index_bytes = b"".join(struct.pack("<II", off, size) for off, size in offsets)
    data_bytes = b"".join(frame_blobs)
    crc = zlib.crc32(index_bytes + data_bytes) & 0xFFFFFFFF

    header = bytearray(header_size)
    header[0:4] = b"BNF1"
    struct.pack_into("<HH", header, 4, 1, 0)
    struct.pack_into("<HHHH", header, 8, logical_size[0], logical_size[1], output_size[0], output_size[1])
    struct.pack_into("<HHHH", header, 16, fps, frame_count, loop_start_zero, loop_end_zero)
    struct.pack_into("<HH", header, 24, 1, 0)  # format=1 RGB565_RLE_DIRTY
    struct.pack_into("<I", header, 28, index_offset)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, crc)
    struct.pack_into("<I", header, 40, header_size)

    output_path.write_bytes(header + index_bytes + data_bytes)
    return output_path.stat().st_size


def make_contact_sheet(frames: Sequence[Path], output: Path, count: int = 16) -> None:
    if count <= 0:
        return
    selected = np.linspace(0, len(frames) - 1, min(count, len(frames)), dtype=int)
    thumb_w, thumb_h = 180, 120
    cols = 4
    rows = math.ceil(len(selected) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (255, 255, 255))

    for i, idx in enumerate(selected):
        im = Image.open(frames[int(idx)]).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, 84, 18), fill=(0, 0, 0))
        draw.text((4, 2), f"frame {int(idx) + 1}", fill=(255, 255, 255))
        sheet.paste(im, ((i % cols) * thumb_w, (i // cols) * thumb_h))

    sheet.save(output, quality=90)


def parse_size(s: str) -> Tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", s.lower().strip())
    if not match:
        raise argparse.ArgumentTypeError("expected format WIDTHxHEIGHT, e.g. 360x240")
    return int(match.group(1)), int(match.group(2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert frames or MP4/video into BNF1 .banim.")
    parser.add_argument("input", type=Path, help="Input frame directory, .zip, or video file such as .mp4")
    parser.add_argument("output", type=Path, help="Output .banim path")
    parser.add_argument("--fps", type=int, help="Animation FPS. Required for frame folders/zips. Optional for video; auto-detected if omitted")
    parser.add_argument("--loop-start", type=int, required=True, help="Loop start frame, 1-based. Example: 180")
    parser.add_argument("--logical-size", type=parse_size, default=None, help="Logical frame size, e.g. 360x240. Default: auto-detect from first frame/video frame")
    parser.add_argument("--output-size", type=parse_size, default=None, help="Target display size stored in header, e.g. 720x480. Default: same as logical size")
    parser.add_argument("--resize", choices=["none", "nearest", "lanczos"], default="none", help="Resize frames to logical size if needed")
    parser.add_argument("--rect-mode", choices=["bbox", "rows"], default="rows", help="Dirty rect mode. rows is usually smaller, bbox is simplest")
    parser.add_argument("--merge-factor", type=float, default=1.15, help="Row-rect merge factor. Higher means fewer/larger rects")
    parser.add_argument("--report", type=Path, help="Write analysis JSON report")
    parser.add_argument("--contact-sheet", type=Path, help="Write JPG contact sheet")
    parser.add_argument("--export-first-frame", type=Path, help="Export the original first frame before resize. Extension decides format, e.g. .png or .bmp")
    parser.add_argument("--export-knulli-bootlogo", type=Path, help="Export bootlogo.bmp from selected logo source")
    parser.add_argument("--export-muos-logo", type=Path, help="Export muoslogo.ico from selected logo source")
    parser.add_argument("--ico-sizes", type=parse_ico_sizes, default=[64, 128, 256], help="Comma-separated ICO sizes for --export-muos-logo. Default: 64,128,256")
    parser.add_argument("--logo-source", choices=["banim", "source"], default="banim", help="Source for logo exports. Default: banim frame 0 after logical resize/RGB565 quantization. Use source for original first frame before resize.")
    parser.add_argument("--logo-size", type=parse_size, default=None, help="Resize exported boot logo to WxH. If omitted, keeps chosen logo source size.")
    parser.add_argument("--logo-resize", choices=["none", "nearest", "lanczos"], default="lanczos", help="Resize method for --logo-size. Default: lanczos")
    parser.add_argument("--keep-temp", action="store_true", help="Keep extracted temp dir when input is zip or video")
    args = parser.parse_args(argv)

    frames, temp_dir, input_meta = collect_frames(args.input)

    fps = args.fps
    if fps is None:
        if input_meta.get("input_type") == "video":
            fps = int(input_meta["detected_fps"])
        else:
            raise SystemExit("--fps is required for frame directories and zip files. For video input it can be auto-detected.")

    if fps <= 0 or fps > 240:
        raise SystemExit("FPS must be between 1 and 240")

    logical_size = args.logical_size or image_size(frames[0])
    output_size_arg = args.output_size or logical_size

    try:
        first_source_image = None
        logo_image_from_source = None
        if (args.export_first_frame or args.export_knulli_bootlogo or args.export_muos_logo) and args.logo_source == "source":
            logo_image_from_source = load_source_frame_rgb(frames[0])
            if args.logo_size is not None and logo_image_from_source.size != args.logo_size:
                logo_image_from_source = resize_rgb_image(logo_image_from_source, args.logo_size, args.logo_resize)

        frame_blobs, stats = encode_frames(
            frames=frames,
            logical_size=logical_size,
            resize_mode=args.resize,
            rect_mode=args.rect_mode,
            merge_factor=args.merge_factor,
        )

        output_size = build_bnf1(
            frame_blobs=frame_blobs,
            output_path=args.output,
            logical_size=logical_size,
            output_size=output_size_arg,
            fps=fps,
            loop_start_1based=args.loop_start,
        )

        if args.export_first_frame or args.export_knulli_bootlogo or args.export_muos_logo:
            logo_image = logo_image_from_source if args.logo_source == "source" else prepare_logo_image_from_banim(args.output, args.logo_size, args.logo_resize)

        if args.export_first_frame:
            args.export_first_frame.parent.mkdir(parents=True, exist_ok=True)
            logo_image.save(args.export_first_frame)

        if args.export_knulli_bootlogo:
            save_bootlogo_bmp_from_image(logo_image, args.export_knulli_bootlogo)

        if args.export_muos_logo:
            save_muos_ico_from_image(logo_image, args.export_muos_logo, args.ico_sizes)

        loop_zero = max(0, min(len(frames) - 1, args.loop_start - 1))
        loop_transition_identical = False
        if stats["last_frame"] is not None:
            loop_frame = load_frame_rgb565(frames[loop_zero], logical_size, args.resize)
            loop_transition_identical = bool(np.array_equal(stats["last_frame"], loop_frame))

        report = {
            "input": str(args.input),
            "input_type": input_meta.get("input_type"),
            "detected_fps_exact": input_meta.get("detected_fps_exact"),
            "detected_fps_raw": input_meta.get("detected_fps_raw"),
            "fps_written_to_banim": fps,
            "output": str(args.output),
            "frame_count": len(frames),
            "logical_size": list(logical_size),
            "output_size": list(output_size_arg),
            "first_frame_source_size": list(image_size(frames[0])),
            "export_first_frame": str(args.export_first_frame) if args.export_first_frame else None,
            "export_knulli_bootlogo": str(args.export_knulli_bootlogo) if args.export_knulli_bootlogo else None,
            "export_muos_logo": str(args.export_muos_logo) if args.export_muos_logo else None,
            "logo_source": args.logo_source,
            "logo_size": list(args.logo_size) if args.logo_size else None,
            "logo_resize": args.logo_resize,
            "loop_start_frame_1_based": args.loop_start,
            "loop_start_frame_0_based": loop_zero,
            "loop_transition_last_to_loop_start_identical_rgb565": loop_transition_identical,
            "raw_rgb565_all_frames_bytes": logical_size[0] * logical_size[1] * 2 * len(frames),
            "banim_size_bytes": output_size,
            "full_frame_rgb565_rle_bytes_estimate": stats["full_frame_rgb565_rle_bytes_estimate"],
            "frames_with_no_change": stats["frames_with_no_change"],
            "min_frame_payload": stats["min_frame_payload"],
            "max_frame_payload": stats["max_frame_payload"],
            "avg_frame_payload": stats["avg_frame_payload"],
            "rect_mode": args.rect_mode,
            "format": "BNF1 RGB565 dirty rectangles + RLE [count:u8, color:u16le]",
        }

        if args.report:
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if args.contact_sheet:
            make_contact_sheet(frames, args.contact_sheet)

        print(f"Input type: {input_meta.get('input_type')}")
        if input_meta.get("input_type") == "video":
            print(f"Detected FPS: {input_meta.get('detected_fps_exact'):.6g} ({input_meta.get('detected_fps_raw')})")
        print(f"Frames: {len(frames)}")
        print(f"FPS written: {fps}")
        print(f"Loop start: frame {args.loop_start} (zero-based {loop_zero})")
        print(f"Output: {args.output}")
        print(f"Size: {output_size:,} bytes ({output_size / (1024 * 1024):.2f} MiB)")
        print(f"Loop transition identical RGB565: {loop_transition_identical}")
        if args.report:
            print(f"Report: {args.report}")
        if args.contact_sheet:
            print(f"Contact sheet: {args.contact_sheet}")
        if args.export_first_frame:
            print(f"First frame: {args.export_first_frame}")
        if args.export_knulli_bootlogo:
            print(f"Knulli bootlogo BMP: {args.export_knulli_bootlogo}")
        if args.export_muos_logo:
            print(f"muOS ICO logo: {args.export_muos_logo}")

        return 0
    finally:
        if temp_dir and not args.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        elif temp_dir:
            print(f"Temporary frames kept at: {temp_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
