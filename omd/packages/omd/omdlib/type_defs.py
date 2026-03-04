#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum

Config = dict[str, str]
Replacements = dict[str, str]


class Skeleton(enum.Enum):
    INSTALL = "install"
    KEEPOLD = "keepold"
    ABORT = "abort"
    ASK = "ask"
