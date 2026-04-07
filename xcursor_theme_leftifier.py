#!/usr/bin/env python3
"""Make cursor theme left-handed. Uses own heuristics to choose which cursors to flip"""
"""Allows overriding the heuristics by providing own comma-separated --files list"""

import argparse
import shutil
from configparser import ConfigParser
from pathlib import Path
from xcursor_format import XCursor

ALWAYS_MIRROR = {
    "hand1", "hand2", "grab", "openhand", "closedhand", "grabbing",
    "pointer", "pointing_hand",
    "dnd-ask",
}

NEVER_MIRROR = {
    "sb_left_arrow", "sb_right_arrow",
    "left-arrow", "right-arrow",
    "left_tee", "right_tee",
    "ul_angle", "ur_angle", "ll_angle", "lr_angle",
    "right_ptr",
    "bottom_left_corner", "top_left_corner", "top_right_corner", "bottom_right_corner",
    "left_side", "left_tee",
    "right_side", "right_tee",
    "top_side", "top_tee",
    "bottom_side", "bottom_tee",
}

def should_mirror(name: str, xcursor: XCursor, user_list: set | None) -> bool:
    if user_list is not None:
        return name in user_list
    if name in NEVER_MIRROR:
        return False
    if name in ALWAYS_MIRROR:
        return True
    frame = xcursor.largest_image.body
    return frame.xhot / frame.width < 0.4

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', type=Path, required=True)
    parser.add_argument('--output', '-o', type=Path, required=True)
    parser.add_argument('--files', type=lambda s: set(s.split(',')))

    args = parser.parse_args()
    input_dir: Path = args.input
    output_dir: Path = args.output

    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(args.input, args.output, symlinks=True)

    for path in (output_dir / "cursors").iterdir():
        if path.is_file() and not path.is_symlink():
            print(f"Processing {path}")
            name = path.stem
            try:
                xcursor = XCursor(path.read_bytes())
                if should_mirror(name, xcursor, args.files):
                    xcursor.flip()
                    path.write_bytes(xcursor.serialize())
                    print("Flipped")
                else:
                    print("Skipped")
            except Exception as e:
                print("Irrelevant")

    cfg = ConfigParser()
    cfg.read(output_dir / "index.theme")
    lh_theme = f"[LeftHanded] {cfg['Icon Theme']['name']}"
    cfg['Icon Theme']['name'] = lh_theme
    with open(output_dir / "index.theme", "w") as f:
        cfg.write(f, space_around_delimiters=False)

if __name__ == '__main__':
    main()
