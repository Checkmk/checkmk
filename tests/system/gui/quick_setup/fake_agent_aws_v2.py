#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys


def main() -> int:
    sys.stdout.write(
        """
<<<aws_v2_ebs_limits:cached(1633329627,300)>>>
[["block_store_snapshots", "Block store snapshots", 100000, 3, "eu-central-1"], ["block_store_space_gp3", "Storage space of General Purpose SSD (gp3) volumes", 50, 8, "eu-central-1"]]
    """.strip()
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
