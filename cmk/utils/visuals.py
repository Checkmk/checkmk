#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths


def invalidate_visuals_cache():
    """Invalidate visuals cache to use the current data"""
    for file in cmk.utils.paths.visuals_cache_dir.glob("last*"):
        file.unlink(missing_ok=True)
