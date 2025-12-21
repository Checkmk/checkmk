#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Load plug-in names into this module to have a single set of default settings

from .alert_handling import *  # noqa: F403
from .base import *  # noqa: F403
from .cmc import *  # noqa: F403
from .customer import *  # noqa: F403
from .notify import *  # noqa: F403
from .relays import *  # noqa: F403
