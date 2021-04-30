#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
These functions allow checks to keep a memory until the next time
the check is being executed. The most frequent use case is compu-
tation of rates from two succeeding counter values.

While a host is being checked this memory is kept in _global_state.

Note: The item state is kept in tmpfs and not reboot-persistant.
Do not store long-time things here. Also do not store complex
structures like log files or stuff.
"""

from ._utils import ValueStoreManager
from ._global_state import get_value_store, load_host_value_store

__all__ = [
    "get_value_store",
    "load_host_value_store",
    "ValueStoreManager",
]
