#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is a collector for elements from misc.py - formerly ../utils.py and exists for
compatibility reasons.
Add code to separate modules instead of adding them here or in misc.py.
After everything done this file should be empty!
"""

from .misc import (
    _NullContext,
    AgentJSON,
    DataCache,
    datetime_serializer,
    get_seconds_since_midnight,
    vcrtrace,
)
