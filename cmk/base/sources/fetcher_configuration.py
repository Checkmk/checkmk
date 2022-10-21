#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Iterable, Tuple

from cmk.utils.type_defs import HostName

from cmk.core_helpers import Fetcher, FetcherType
from cmk.core_helpers.cache import FileCache, MaxAge
from cmk.core_helpers.type_defs import SourceInfo

__all__ = ["fetchers", "clusters"]


def fetchers(sources: Iterable[Tuple[SourceInfo, FileCache, Fetcher]]) -> Dict[str, Any]:
    return {
        "fetchers": [
            {
                "source": {
                    "hostname": source.hostname,
                    "ipaddress": source.ipaddress,
                    "ident": source.ident,
                    "fetcher_type": source.fetcher_type.name,
                    "source_type": source.source_type.name,
                },
                "fetcher_params": fetcher.to_json(),
                "file_cache_params": type(file_cache)(
                    file_cache.hostname,
                    path_template=file_cache.path_template,
                    # During discovery, the allowed cache age defaults to 120 seconds,
                    # such that the discovery service won't steal data for TCP.
                    # For SNMP, we do want to see new services so we invalidate the cache
                    # immediately.
                    # For TCP, we ensure the cache gets updated by triggering the "Check_MK"
                    # service when the "Check_MK Discovery" is triggered and use the newly
                    # cached data during the discovery.
                    max_age=(
                        MaxAge.none()
                        if source.fetcher_type is FetcherType.SNMP
                        else file_cache.max_age
                    ),
                    use_outdated=file_cache.use_outdated,
                    simulation=file_cache.simulation,
                    use_only_cache=file_cache.use_only_cache,
                    file_cache_mode=file_cache.file_cache_mode,
                ).to_json(),
            }
            for source, file_cache, fetcher in sources
        ]
    }


def clusters(nodes: Iterable[HostName]) -> Dict[str, Any]:
    return {"clusters": {"nodes": list(nodes)}}
