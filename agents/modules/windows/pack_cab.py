#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pack a directory tree into a Microsoft Cabinet (MSZIP-compressed).

Replaces the historical ``makecab.exe`` invocation in the windows agent's
python-3.cab build with a pure-Python equivalent (@cabarchive), so the build
is hermetic and runs on Linux.  The container metadata mirrors what makecab
produced, so the agent-side ``expand <cab> -F:* <dir>`` extraction sees the
same shape:

* CFFILE names are backslash-separated with a leading ``\\`` (makecab style),
* root-level files are listed before the directory trees,
* every member carries the DOS *archive* attribute (0x20),
* all timestamps are a fixed constant, so rebuilding the same inputs yields a
  bit-identical cabinet (makecab stamped build wall-clock times instead).

The one deliberate difference: compression is MSZIP, not makecab's LZX:18.
No maintained Linux tool can *write* LZX (cabextract/libmspack only read it;
gcab and cabarchive write MSZIP at most) — costs ~20% cabinet size, which we
accept; ``expand`` handles both.

Usage::

    pack_cab.py --root path/to/tree --out path/to/output.cab
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from cabarchive import CabArchive, CabFile  # type: ignore[attr-defined]

# Fixed member timestamp (DOS time: 2s resolution, no timezone).  Deliberately
# an obviously-synthetic constant: the historic CABs carried the build
# machine's wall-clock time, which nothing consumes but which made the output
# unreproducible.
_FIXED_MTIME = datetime.datetime(2026, 1, 1, 0, 0, 0)

# The cabinet "set ID" is an arbitrary tag makecab picked per run; it only
# matters for multi-volume sets (which this never is).  Use the value observed
# in the historic production cabs so the container metadata diff stays empty.
_SET_ID = 4171


def _cab_name(rel: Path) -> str:
    # CFFILE name, makecab style: leading backslash, backslash separators.
    return "\\" + str(rel).replace("/", "\\")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="directory whose contents to pack")
    parser.add_argument("--out", required=True, type=Path, help="output .cab path")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"error: {args.root} is not a directory", file=sys.stderr)
        return 1

    # makecab's directive enumerated the install root's files first, then the
    # subdirectory trees; order is functionally irrelevant for extraction but
    # we keep the same layout.  Sorting makes the output deterministic.
    files = sorted(
        (p for p in args.root.rglob("*") if p.is_file()),
        key=lambda p: (
            len(p.relative_to(args.root).parts) > 1,
            _cab_name(p.relative_to(args.root)),
        ),
    )

    arc = CabArchive()
    arc.set_id = _SET_ID
    for path in files:
        cab_file = CabFile(path.read_bytes(), mtime=_FIXED_MTIME)
        cab_file.is_arch = True
        arc[_cab_name(path.relative_to(args.root))] = cab_file

    args.out.write_bytes(arc.save(compress=True, sort=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
