#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file is for execution by the pre-commit framework.

import os
import re
import sys
from pathlib import PurePosixPath
from typing import List

WHITELIST = ("cmk/gui",)

if __name__ == "__main__":
    fails: List[str] = []
    for filename in sys.argv[1:]:
        if str(PurePosixPath(filename).parent) not in WHITELIST:
            continue
        fails.extend([filename for line in open(filename) if re.match("^(from|import) \\.", line)])
    if fails:
        sys.stderr.write(f"error: These files are using relative imports: {fails}" + os.linesep)
        sys.stderr.write("We currently mandate absolute imports. Please use them." + os.linesep)
        sys.stderr.flush()
        sys.exit(1)
    sys.stderr.flush()
    sys.exit(0)
