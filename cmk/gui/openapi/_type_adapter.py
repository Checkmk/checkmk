#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import ConfigDict, TypeAdapter

_g_type_adapters: dict[tuple[type, str], TypeAdapter] = {}


def get_cached_type_adapter[T](
    type_: type[T], *, config: ConfigDict | None = None
) -> TypeAdapter[T]:
    """Get a cached TypeAdapter for the given type."""
    # The REST API uses TypeAdapters in the following contexts:
    # * Validation of incoming request data (once for every request)
    # * Serialization of outgoing response data (once for every non-empty response)
    # * Generation of OpenAPI schema
    # Since creating a TypeAdapter is relatively expensive, we cache them to increase performance
    # of recurring requests. The schema generation is not performance-critical, but this still leads
    # to a 2x performance improvement (with few migrated endpoints).
    key = (type_, str(config))
    if key not in _g_type_adapters:
        _g_type_adapters[key] = TypeAdapter(  # nosemgrep: type-adapter-detected
            type_, config=config
        )
    return _g_type_adapters[key]


__all__ = [
    "get_cached_type_adapter",
]
