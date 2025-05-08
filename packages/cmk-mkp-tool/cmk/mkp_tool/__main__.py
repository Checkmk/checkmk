#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Command line interface for the Checkmk Extension Packages"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
