#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.checkengine.filecache import FileCacheOptions
from cmk.plugins.checkmk.cli.options import FileCacheRequest, make_file_cache_options


def test_without_cache_options_the_defaults_stand() -> None:
    assert make_file_cache_options(
        FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
        defaults=FileCacheOptions(disabled=True),
    ) == FileCacheOptions(disabled=True)


def test_cache_uses_outdated_cache_files() -> None:
    assert make_file_cache_options(
        FileCacheRequest(cache=True, no_cache=False, no_tcp=False)
    ) == FileCacheOptions(disabled=False, use_outdated=True)


def test_no_cache_disables_the_cache() -> None:
    assert make_file_cache_options(
        FileCacheRequest(cache=False, no_cache=True, no_tcp=False)
    ) == FileCacheOptions(disabled=True, use_outdated=False)


def test_no_tcp_uses_only_cache_files() -> None:
    assert make_file_cache_options(
        FileCacheRequest(cache=False, no_cache=False, no_tcp=True)
    ) == FileCacheOptions(disabled=False, use_outdated=True, use_only_cache=True)
