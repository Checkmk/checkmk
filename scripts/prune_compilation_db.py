#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Remove useless and duplicate entries from the compilation database, effectively
# bringing it down to only 5% of its original size.

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

COMPILATION_DB: Final = Path("compile_commands.json")
COMPILATION_DB_PRUNED: Final = COMPILATION_DB
SUFFIXES_TO_KEEP: Final = (".c", ".cc", ".cpp", ".cxx")
DIRS_TO_KEEP: Final = (Path("packages"), Path("non-free/packages"))


# https://github.com/hedronvision/bazel-compile-commands-extractor generates only a subset
# of the keys specified in https://clang.llvm.org/docs/JSONCompilationDatabase.html
@dataclass(frozen=True)
class Entry:
    file: str
    directory: str
    arguments: tuple[str]


with COMPILATION_DB.open() as fp:
    pruned_db = [
        asdict(entry)
        for entry in sorted(
            {
                entry
                for entry_dict in json.load(fp)
                for entry in (
                    Entry(
                        file=entry_dict["file"],
                        directory=entry_dict["directory"],
                        arguments=tuple(entry_dict["arguments"]),
                    ),
                )
                if Path(entry.file).suffix.lower() in SUFFIXES_TO_KEEP
                and any(Path(entry.file).is_relative_to(d) for d in DIRS_TO_KEEP)
            },
            key=lambda e: e.file,
        )
    ]

with COMPILATION_DB_PRUNED.open(mode="w") as fp:
    json.dump(pruned_db, fp, indent=2)
