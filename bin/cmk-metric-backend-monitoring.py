#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path

from cmk.metric_backend import monitor


def main() -> int:
    site_id = os.environ["OMD_SITE"]
    config = monitor.get_config_if_self_hosted(Path(os.environ["OMD_ROOT"]))
    if not config:
        return 0

    request = monitor.make_ping_section(site_id, config)
    sys.stdout.write("<<<metric_backend_omd_ping:sep(0)>>>\n")
    sys.stdout.write(request.model_dump_json() + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
