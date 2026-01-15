#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from functools import lru_cache

from pydantic import ConfigDict, TypeAdapter


class _HashableArgs[T]:
    """A class to make the arguments of `get_cached_type_adapter` hashable, so they can be used with
    the `lru_cache`. This is necessary because `ConfigDict` does not implement `__hash__`."""

    __slots__ = ("type", "config")

    def __init__(self, type_: type[T], config: ConfigDict | None = None) -> None:
        self.type = type_
        self.config = config

    def __hash__(self) -> int:
        return hash((self.type, str(self.config)))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _HashableArgs)
            and self.type == other.type
            and self.config == other.config
        )


@lru_cache(maxsize=128)  # arbitrarily chosen, should be ~2x of what EndpointModel.build uses
def _get_type_adapter[T](args: _HashableArgs[T]) -> TypeAdapter[T]:
    """Get a TypeAdapter for the given type."""
    # nosemgrep: type-adapter-detected
    return TypeAdapter(args.type, config=args.config)


def get_cached_type_adapter[T](
    type_: type[T], *, config: ConfigDict | None = None
) -> TypeAdapter[T]:
    """Get a cached TypeAdapter for the given type."""
    # The REST API uses TypeAdapters in the following contexts:
    # * Validation of incoming request data (once for every request)
    # * Serialization of outgoing response data (once for every non-empty response)
    # * Generation of the OpenAPI schema
    # Since creating a TypeAdapter is relatively expensive, we cache them to increase performance
    # of recurring requests.
    return _get_type_adapter(_HashableArgs(type_, config=config))


__all__ = [
    "get_cached_type_adapter",
]
