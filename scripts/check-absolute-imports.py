#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file is for execution by the pre-commit framework.

import re
import sys
from pathlib import Path

WHITELIST = (Path("cmk/gui"),)

if __name__ == "__main__":
    fails: list[str] = []
    for filename in sys.argv[1:]:
        if Path(filename).parent in WHITELIST:
            with open(filename, encoding="utf-8") as f:
                fails.extend(filename for line in f if re.match("^(from|import) \\.", line))
    if fails:
        sys.stderr.write(f"error: These files are using relative imports: {fails}\n")
        sys.stderr.write("We currently mandate absolute imports. Please use them.\n")
        sys.stderr.flush()
        sys.exit(1)
    sys.stderr.flush()
    sys.exit(0)
