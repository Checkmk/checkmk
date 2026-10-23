#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Deprecated alias for :mod:`cmk.server_side_programs.v1`.

This namespace is kept for backwards compatibility only.
It will be removed in Checkmk 3.1.
Import from :mod:`cmk.server_side_programs.v1` instead.
"""

from cmk.server_side_programs.v1 import *  # noqa: F403
from cmk.server_side_programs.v1 import __all__ as __all__
