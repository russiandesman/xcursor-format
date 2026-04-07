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

def should_mirror_by_names(all_names: set[str], xcursor: XCursor, user_list: set | None) -> bool:
    """Determine if file should be mirrored based on all its names (direct + symlinks)."""
    # User override takes precedence
    if user_list is not None:
        return any(name in user_list for name in all_names)

    # If ANY name is in NEVER_MIRROR, don't flip (conservative approach)
    if any(name in NEVER_MIRROR for name in all_names):
        return False

    # If ANY name is in ALWAYS_MIRROR, flip
    if any(name in ALWAYS_MIRROR for name in all_names):
        return True

    # Fall back to heuristic
    frame = xcursor.largest_image.body
    return frame.xhot / frame.width < 0.4

def build_reverse_symlink_map(cursors_dir: Path) -> dict[Path, set[str]]:
    """Map each real file to all symlink names pointing to it."""
    file_to_symlinks = {}

    for path in cursors_dir.iterdir():
        if path.is_symlink():
            try:
                target = path.resolve()
                if target not in file_to_symlinks:
                    file_to_symlinks[target] = set()
                file_to_symlinks[target].add(path.stem)
            except (OSError, RuntimeError):
                # Broken symlink, skip
                pass

    return file_to_symlinks

def check_for_conflicts(file_to_symlinks: dict[Path, set[str]]) -> dict[Path, tuple[set[str], set[str]]]:
    """Identify files with conflicting symlink rules.

    Returns a dict mapping conflicted files to (always_names, never_names) tuples.
    """
    conflicted_files = {}

    for target, symlink_names in file_to_symlinks.items():
        always_names = symlink_names & ALWAYS_MIRROR
        never_names = symlink_names & NEVER_MIRROR
        if always_names and never_names:
            conflicted_files[target] = (always_names, never_names)

    return conflicted_files


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

    cursors_dir = output_dir / "cursors"

    # Build reverse symlink map
    file_to_symlinks = build_reverse_symlink_map(cursors_dir)

    # Check for conflicts and warn
    # Check for conflicts and warn
    conflicted_files = check_for_conflicts(file_to_symlinks)
    if conflicted_files:
        print("WARNING: Conflicting symlinks detected (same file with ALWAYS_MIRROR and NEVER_MIRROR names):")
        for target, (always, never) in sorted(conflicted_files.items(), key=lambda x: x[0].name):
            print(f"  {target.name}")
            print(f"    ALWAYS_MIRROR: {sorted(always)}")
            print(f"    NEVER_MIRROR: {sorted(never)}")
        print("  NEVER_MIRROR takes precedence. Use --files to override.")
        print()

    for path in cursors_dir.iterdir():
        if path.is_file() and not path.is_symlink():
            name = path.stem
            symlink_names = file_to_symlinks.get(path, set())
            all_names = {name} | symlink_names

            print(f"Processing {path.name}", end="")
            if symlink_names:
                print(f" (also: {', '.join(sorted(symlink_names))})", end="")
            print()

            try:
                xcursor = XCursor(path.read_bytes())
                if should_mirror_by_names(all_names, xcursor, args.files):
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
