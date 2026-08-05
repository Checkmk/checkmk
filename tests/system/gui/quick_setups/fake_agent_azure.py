#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys


def main() -> int:
    sys.stdout.write(
        """
<<<azure_agent_info:sep(124)>>>
remaining-reads|249
    """.strip()
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
