#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is the python module hierarchy used by Check_MK's core
components, former called modules. This hosts the checking,
discovery and a lot of other functionality."""

from .caching import CacheManager

# This cache manager holds all caches that rely on the configuration
# and have to be flushed once the configuration is reloaded in the
# keepalive mode
config_cache = CacheManager()

# These caches are not automatically cleared during the whole execution
# time of the current Check_MK process. Single cached may be cleaned
# manually during execution.
runtime_cache = CacheManager()
