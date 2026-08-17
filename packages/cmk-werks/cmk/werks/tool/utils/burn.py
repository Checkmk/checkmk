#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path

from cmk.werks.tool import parse_werk

from ..config import RuntimeConfiguration
from ..constants import NON_WERK_FILES_IN_WERK_FOLDER
from ..format import format_as_markdown_werk


def main(repo_root: Path) -> None:
    rc = RuntimeConfiguration(repo_root)
    version_to_be_burned = rc.get_defines_make_version()

    werk_dir: Path = repo_root / ".werks"

    count = 0
    for werk_file in werk_dir.iterdir():
        if werk_file.name in NON_WERK_FILES_IN_WERK_FOLDER:
            continue
        try:
            parsed = parse_werk(werk_file.read_text(), werk_file.name)
        except Exception as e:
            raise RuntimeError(f"file {werk_file} can not be parsed as werk") from e

        if "version" not in parsed.metadata:
            parsed.metadata["version"] = version_to_be_burned
            werk_file.write_text(format_as_markdown_werk(parsed))
            count += 1

    sys.stdout.write(f"Burned {count} Werks.\n")
