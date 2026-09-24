#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path

from .run import run, Runtime


def main() -> int:
    match os.environ.get("OMD_ROOT"):
        case None:
            sys.stderr.write("Checkmk can be used only as site user.\n")
            return 1
        case omd_root:
            return run(Path(omd_root), sys.argv, os.environ, Runtime())
