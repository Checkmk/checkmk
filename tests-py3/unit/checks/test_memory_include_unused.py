#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# coding=utf-8
import subprocess
import sys

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import


def test_no_callsite():
    path = Path(__file__, '../../../../checks').resolve()
    exit_code = subprocess.call(["grep", "-rl", "'memory.include'", str(path)])
    assert exit_code == 1  # nothing found
