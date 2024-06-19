#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Load plug-in names into this module to have a single set of default settings
# pylint: disable=wildcard-import,unused-wildcard-import

from .base import *
from .notify import *

try:
    from .cee import *
except ImportError:
    pass  # It's OK in non CEE editions

try:
    from .cme import *
except ImportError:
    pass  # It's OK in non CME editions
