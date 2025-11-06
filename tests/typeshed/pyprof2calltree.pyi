#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pstats
from typing import IO

class CalltreeConverter:
    def __init__(self, profiling_data: str | pstats.Stats) -> None: ...
    def output(self, out_file: IO[str]) -> None: ...
