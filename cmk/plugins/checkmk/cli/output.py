#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import sys
from contextlib import suppress


def write_stdout(text: str) -> None:
    with suppress(IOError):
        sys.stdout.write(text)
        sys.stdout.flush()
