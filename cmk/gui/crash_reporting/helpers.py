#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence


def local_files_involved_in_crash(exc_traceback: Sequence[Sequence[object]]) -> list[str]:
    return [
        filepath
        for frame in exc_traceback
        if len(frame) == 4 and isinstance(filepath := frame[0], str) and "/local/" in filepath
    ]
