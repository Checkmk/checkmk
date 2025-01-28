#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Load plug-in names into this module to have a single set of default settings

from .base import *  # noqa: F403
from .notify import *  # noqa: F403

try:
    from .cee import *  # type: ignore[import-untyped, unused-ignore]  # noqa: F403
except ImportError:
    pass  # It's OK in non CEE editions

try:
    from .cme import *  # type: ignore[import-untyped, unused-ignore]  # noqa: F403
except ImportError:
    pass  # It's OK in non CME editions
