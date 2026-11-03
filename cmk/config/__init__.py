#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Access to the Checkmk configuration

This package is meant to become the interface through which all
configuration read and write operations go.
We are currently far away from that long term goal.
"""

from ._legacy_default_base_config import (
    get_legacy_default_base_config as get_legacy_default_base_config,
)
