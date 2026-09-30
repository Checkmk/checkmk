#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import load_werk
from .config import load_config, try_load_current_version_from_defines_make
from .constants import NON_WERK_FILES_IN_WERK_FOLDER


def main(
    werks_to_check: Sequence[Path],
    werks_config: Path,
    defines_make: Path,
    version_regex: re.Pattern[str],
) -> None:
    current_version = try_load_current_version_from_defines_make(defines_make)
    config = load_config(werks_config, current_version=current_version)
    choices_component = {e[0] for e in config.all_components()}

    for werk_path in werks_to_check:
        if werk_path.name in NON_WERK_FILES_IN_WERK_FOLDER:
            sys.stdout.write(f"WARNING: NOT CHECKING {werk_path} as it's not a werk.\n")
            continue
        werk_content = werk_path.read_text(encoding="utf-8")
        try:
            werk = load_werk(file_content=werk_content, file_name=werk_path.name)

            if werk.component not in choices_component:
                raise ValueError(
                    f"Component {werk.component!r} not defined in config.\n"
                    f"Available values: {choices_component!r}"
                )
            if werk.version is not None and not version_regex.match(werk.version):
                raise ValueError(f"Version {werk.version!r} is not valid")

        except Exception as e:
            raise RuntimeError(f"Error while loading werk {werk_path}\n\n{werk_content}") from e

    sys.stdout.write(f"Successfully validated {len(werks_to_check)} werks\n")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version-regex",
        help="regex used to validate the version in the werk",
        default=r"^\d.\d.\d([ipb]\d+)?$",
        type=re.compile,
    )
    parser.add_argument(
        "--werk-config",
        help="path to werks config, typically .werks/config",
        default=".werks/config",
        type=Path,
    )
    parser.add_argument(
        "--defines-make",
        help="path to defines.make to load current version, typically defines.make",
        default="defines.make",
        type=Path,
    )
    parser.add_argument(
        "werk_paths",
        help="werk paths to validate, can also be passed via $CHANGED_WERK_FILES",
        nargs="*",
        type=Path,
    )
    return parser.parse_args(argv)


def _werks_to_check(
    werk_paths: Sequence[Path], changed_werk_files: str | None, working_dir: Path
) -> Sequence[Path]:
    if werk_paths:
        return [working_dir / path for path in werk_paths]
    if changed_werk_files:
        return [working_dir / line for line in changed_werk_files.split(" ") if line]
    return [
        path
        for path in (working_dir / ".werks").iterdir()
        if path.name.isdigit() or path.name.endswith(".md")
    ]


def run(argv: Sequence[str], environ: Mapping[str, str], working_dir: Path) -> None:
    args = parse_args(argv)
    main(
        _werks_to_check(args.werk_paths, environ.get("CHANGED_WERK_FILES"), working_dir),
        working_dir / args.werk_config,
        working_dir / args.defines_make,
        args.version_regex,
    )


if __name__ == "__main__":
    run(sys.argv[1:], os.environ, Path.cwd())
