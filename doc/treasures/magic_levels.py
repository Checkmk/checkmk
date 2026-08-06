#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Print the file system levels that the 'magic factor' computes for a set of sizes.

Usage: magic_levels.py [NORMSIZE_GB] [--markdown]
"""

import sys

# Sizes in GB used for the columns of the table.
SIZES = [500, 1000, 2000, 5000, 10000, 20000, 50000]

# Magic factors used for the rows of the table.
FACTORS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]

# Base levels (level of the norm partition) for which a table is printed.
BASE_LEVELS = [0.80, 0.85, 0.90, 0.95]

DEFAULT_NORMSIZE = 20.0


def magic_level(level: float, factor: float, size: float, normsize: float) -> float:
    """Return the warning level that the magic factor yields for a given size."""
    relative_size = size / normsize
    felt_size = relative_size**factor
    scale = felt_size / relative_size
    return 1 - ((1 - level) * scale)


def human(size_gb: float) -> str:
    if round(size_gb) >= 1000:
        return f"{size_gb / 1000:.1f} TB".replace(".0 TB", " TB")
    return f"{size_gb:.0f} GB"


def print_plain(normsize: float) -> None:
    for level in BASE_LEVELS:
        print(f"Level for {normsize:.0f} GB norm partition: {int(level * 100)}%")
        for factor in FACTORS:
            cells = []
            for size in SIZES:
                new_level = magic_level(level, factor, size, normsize)
                free = size * (1.0 - new_level)
                cells.append(f"{human(size):>6}:{new_level * 100:5.1f}%({human(free):>6} free)")
            print(f"f={factor:3.1f}: " + " ".join(cells))
        print("-" * 110)


def print_markdown(normsize: float, level: float = 0.80, show_free: bool = False) -> None:
    header = ["Magic factor"] + [human(s) for s in SIZES]
    print(f"Norm size: {human(normsize)}, level of the norm size: {int(level * 100)} %\n")
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    for factor in FACTORS:
        row = [f"{factor:.1f}"]
        for size in SIZES:
            new_level = magic_level(level, factor, size, normsize)
            cell = f"{new_level * 100:.1f} %"
            if show_free:
                cell += f" ({human(size * (1.0 - new_level))})"
            row.append(cell)
        print("| " + " | ".join(row) + " |")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    normsize = float(args[0]) if args else DEFAULT_NORMSIZE
    if "--markdown" in sys.argv:
        print_markdown(normsize, show_free="--free" in sys.argv)
    else:
        print_plain(normsize)


if __name__ == "__main__":
    main()
