#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import shutil
import sys
from pathlib import Path

from cmk.utils import msi_engine
from cmk.utils.paths import bin_dir, tmp_dir

name, msi_in = ast.literal_eval(sys.stdin.read())

out_dir = tmp_dir / "idts"
try:
    out_dir.mkdir()
    msi_engine.opt_verbose = False
    msi_engine._export_msi_file_table(
        bin_dir,
        name=name,
        msi_in=Path(msi_in),
        out_dir=out_dir,
    )
    f = out_dir / f"{name}.idt"

    print(f.stat().st_size)
finally:
    shutil.rmtree(str(out_dir))
