#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Package:
    name: str
    path: str
    command_line: str
    maintainers: list[str] = field(default_factory=lambda: [])
    sec_vars: list[str] = field(default_factory=lambda: [])
    dependencies: list[str] = field(default_factory=lambda: [])

    def __post_init__(self):
        # Fallback for now...
        self.maintainers.append("team-ci@checkmk.com")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("packages_path")
    return parser.parse_args()


def parse_package(meta_file: Path, name: str) -> Package:
    with open(meta_file) as f:
        data = {**json.load(f), "name": name, "path": str(meta_file.parent)}
        return Package(**data)


def discover_packages(args: argparse.Namespace) -> Iterator[Package]:
    for package_dir in Path(args.packages_path).iterdir():
        if not package_dir.is_dir():
            continue
        meta_file = package_dir / "ci.json"
        if not meta_file.exists():
            sys.stderr.write(
                f"Skipping {package_dir} as it does not contain a {meta_file} (yet). "
                f"TODO: Add it to be discovered. \n"
            )
            continue
        try:
            package = parse_package(meta_file, package_dir.name)
        except Exception as e:
            sys.stderr.write(f"Skipping {package_dir} as it has invalid meta data: {e}\n")
            continue
        yield package


def main():
    args = parse_arguments()
    print(json.dumps([asdict(p) for p in discover_packages(args)], indent=2))


if __name__ == "__main__":
    main()
