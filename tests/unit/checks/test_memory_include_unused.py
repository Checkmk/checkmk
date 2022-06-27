#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from pathlib import Path


def test_no_callsite() -> None:
    path = Path(__file__, "../../../../checks").resolve()
    exit_code = subprocess.call(["grep", "-rl", "'memory.include'", str(path)])
    assert exit_code == 1  # nothing found
