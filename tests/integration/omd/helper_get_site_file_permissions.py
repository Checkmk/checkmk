#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import cmk.utils.paths


def iter_dir(path: Path) -> Iterator[tuple[int, Path]]:
    for sub_path in path.iterdir():
        if sub_path.is_symlink():
            continue

        yield sub_path.stat().st_mode, sub_path
        if sub_path.is_dir():
            yield from iter_dir(sub_path)


site_dir = cmk.utils.paths.omd_root
print([(m, str(p.relative_to(site_dir))) for m, p in iter_dir(site_dir)])
