#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path
from stat import S_ISDIR, S_ISLNK

import cmk.utils.paths


def iter_dir(path: Path) -> Iterator[tuple[int, Path]]:
    for sub_path in path.iterdir():
        try:
            mode = sub_path.lstat().st_mode
            if not S_ISLNK(mode):
                yield mode, sub_path
                if S_ISDIR(mode):
                    yield from iter_dir(sub_path)
        except FileNotFoundError:
            pass  # ignore vanished files during iteration


site_dir = cmk.utils.paths.omd_root
print([(m, str(p.relative_to(site_dir))) for m, p in iter_dir(site_dir)])
