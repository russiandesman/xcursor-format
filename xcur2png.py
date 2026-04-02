#!/usr/bin/env python3
"""Extract XCursor files into PNG images + xcursorgen-compatible config."""
"""drop-in replacement for xcur2png (https://github.com/eworm-de/xcur2png)"""

import argparse
from pathlib import Path
from PIL import Image

from xcursor_format import XCursor

def build_png(xcursor_frame, show_hotpoint):
    def unpremultiply(argb):
        def cap(color, a):
            return 0 if a == 0 else min(255, color * 255 // a)
        b = (argb >> 0) & 0xFF
        g = (argb >> 8) & 0xFF
        r = (argb >> 16) & 0xFF
        a = (argb >> 24) & 0xFF
        return cap(r, a), cap(g, a), cap(b, a), a
        
    img = Image.new("RGBA", (xcursor_frame.width, xcursor_frame.height))
    img.putdata([unpremultiply(p) for p in xcursor_frame.pixels])
    if show_hotpoint:
        img.putpixel((xcursor_frame.xhot, xcursor_frame.yhot),(255, 0, 0, 255))

    return img

def main():
    ap = argparse.ArgumentParser(description="Extract XCursor to PNGs")
    ap.add_argument("cursor", help="Input XCursor file")
    ap.add_argument("-o", "--outdir", help="Output directory (default: next to cursor file)")
    ap.add_argument("-c", "--conf", help="Config file path (default: <cursor>.conf)")
    ap.add_argument("-s", "--suffix", type=int, default=0, help="Starting numeric suffix (default: 0)")
    ap.add_argument("-n", "--dry-run", action="store_true")
    ap.add_argument("-x", "--show-hot", action="store_true")
    args = ap.parse_args()

    cursor_path = Path(args.cursor)
    outdir = Path(args.outdir) if args.outdir else cursor_path.parent
    conf_path = Path(args.conf) if args.conf else cursor_path.with_suffix(".conf")
    cursor_bytes = cursor_path.read_bytes()
    xcursor = XCursor(cursor_bytes)

    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)

    suffix = args.suffix
    conf_lines = []

    for image in xcursor.images:
        png_name = f"{cursor_path.stem}_{suffix:03d}.png"
        png_path = outdir / png_name

        try:
            rel_path = png_path.relative_to(conf_path.parent)
        except ValueError:
            rel_path = png_path

        conf_lines.append(f"{image.header.subtype} {image.body.xhot} {image.body.yhot} {rel_path} {image.body.delay}")

        if not args.dry_run:
            img = build_png(image.body, args.show_hot)
            img.save(png_path)
            print(f"  {png_path}")

        suffix += 1

    if not args.dry_run:
        conf_path.write_text("\n".join(conf_lines) + "\n")
        print(f"Config: {conf_path}")
    else:
        print("\n".join(conf_lines))


if __name__ == "__main__":
    main()
