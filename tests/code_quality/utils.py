#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path
from typing import Collection, NamedTuple


class ChangedFiles(NamedTuple):
    test_all_files: bool
    file_paths: Collection[Path]

    def is_changed(self, path: Path) -> bool:
        return self.test_all_files or path in self.file_paths
