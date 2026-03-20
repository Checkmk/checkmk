#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate a JSON mapping from pip package names to their Python import names.

Reads dist-info metadata (METADATA, top_level.txt, RECORD) from pip packages
and produces a JSON file mapping normalized package names to import names.
"""

import argparse
import csv
import json
from pathlib import Path

from tests.code_quality.requirements.utils import normalize


def packagename_for(path: Path) -> str:
    """Check a METADATA file and return the normalized package name."""
    with path.open() as metadata:
        for line in metadata.readlines():
            if line.startswith("Name:"):
                return normalize(line[5:].strip())

    raise ValueError("No 'Name:' in METADATA file")


def importnames_for(packagename: str, path: Path) -> list[str]:
    """Return a list of importable libs which belong to the package."""
    top_level_txt_path = path.with_name("top_level.txt")
    if top_level_txt_path.is_file():
        with top_level_txt_path.open() as top_level_file:
            return [
                normalize(x.strip())
                for x in top_level_file.readlines()
                if x.strip()
                and not x.strip().startswith("_")
                and "-mypyc" not in x
                and "_mypyc" not in x
            ]

    record_path = path.with_name("RECORD")
    if record_path.is_file():
        names = set()
        # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file
        with record_path.open() as record_file:
            reader = csv.reader(record_file, delimiter=",", quotechar='"')
            for row in reader:
                if len(row) != 3:
                    continue
                file_path_str, _file_hash, _file_size = row
                stem = None
                first_part = Path(file_path_str).parts[0]
                if first_part in {"/", "..", "__pycache__"} or first_part.endswith(".dist-info"):
                    continue
                if "-mypyc" in first_part or "_mypyc" in first_part:
                    continue
                if first_part.endswith(".pyi"):
                    continue
                if first_part.endswith(".py"):
                    stem = first_part.removesuffix(".py")
                elif first_part.endswith(".so"):
                    stem = first_part.split(".")[0]
                else:
                    stem = first_part if first_part.isidentifier() else None

                if stem and not stem.startswith("_"):
                    names.add(normalize(stem))
        return list(names)

    return [packagename]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        fromfile_prefix_chars="@",
    )
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument(
        "metadata_files",
        nargs="*",
        help="Paths to METADATA files inside .dist-info directories",
    )
    args = parser.parse_args()

    mapping: dict[str, list[str]] = {}

    for metadata_path_str in args.metadata_files:
        metadata_path = Path(metadata_path_str)
        package_name = packagename_for(metadata_path)
        mapping[package_name] = importnames_for(package_name, metadata_path)

    with open(args.output, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
