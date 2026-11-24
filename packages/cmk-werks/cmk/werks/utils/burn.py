#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path

from cmk.werks import parse_werk

from ..config import try_load_current_version_from_defines_make
from ..format import format_as_werk_v2


def main(repo_root: Path) -> None:
    defines_make = repo_root / "defines.make"
    version_to_be_burned = try_load_current_version_from_defines_make(defines_make)
    if version_to_be_burned is None:
        raise RuntimeError(f"Could not load version from defines.make ({defines_make})")

    count = 0
    for werk_file in (repo_root / ".werks").glob("[0-9]*.md"):
        try:
            parsed = parse_werk(werk_file.read_text(), werk_file.name)
        except Exception as e:
            raise RuntimeError(f"file {werk_file} can not be parsed as werk") from e

        if "version" not in parsed.metadata:
            parsed.metadata["version"] = version_to_be_burned
            werk_file.write_text(format_as_werk_v2(parsed))
            count += 1

    sys.stdout.write(f"Burned {count} Werks.\n")
