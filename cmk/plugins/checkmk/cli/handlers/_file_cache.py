#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.checkengine.filecache import FileCacheOptions
from cmk.plugins.checkmk.cli.options import FileCacheRequest


def make_file_cache_options(
    request: FileCacheRequest, *, defaults: FileCacheOptions | None = None
) -> FileCacheOptions:
    file_cache_options = defaults or FileCacheOptions()

    if request.cache:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True
        )

    if request.no_cache:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=True, use_outdated=False
        )

    if request.no_tcp:
        file_cache_options = dataclasses.replace(
            file_cache_options, disabled=False, use_outdated=True, use_only_cache=True
        )

    return file_cache_options
