#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence


def local_files_involved_in_crash(exc_traceback: Sequence[tuple[str, int, str, str]]) -> list[str]:
    return [filepath for filepath, _lineno, _func, _line in exc_traceback if "/local/" in filepath]
