#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Writes the general version infos to stdout"""

import json
import os
import sys
from pathlib import Path

from .version import get_general_version_infos


def main() -> int:
    sys.stdout.write(json.dumps(get_general_version_infos(_omd_root()), indent=4) + "\n")
    return 0


def _omd_root() -> Path:
    try:
        return Path(os.environ["OMD_ROOT"])
    except KeyError as exc:
        raise RuntimeError(
            "OMD_ROOT environment variable not set. Can only be executed in a Checkmk site."
        ) from exc


if __name__ == "__main__":
    sys.exit(main())
