#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.gui.cmkcert.main import main  # astrein: disable=cmk-module-layer-violation

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
