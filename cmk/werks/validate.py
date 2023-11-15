#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# used as validator for 2.2.0 and 2.1.0 branches

import os
from pathlib import Path

from . import load_werk


def main() -> None:
    if changed_werk_files := os.environ.get("CHANGED_WERK_FILES"):
        werks_to_check = (Path(line) for line in changed_werk_files.split("\n") if line)
    else:
        werks_to_check = (
            path
            for path in Path(".werks").iterdir()
            if path.name.isdigit() or path.name.endswith(".md")
        )

    for werk_path in werks_to_check:
        werk_content = werk_path.read_text(encoding="utf-8")
        try:
            load_werk(file_content=werk_content, file_name=werk_path.name)
        except Exception as e:
            raise RuntimeError(f"Error while loading werk {werk_path}\n{werk_content}") from e


if __name__ == "__main__":
    main()
