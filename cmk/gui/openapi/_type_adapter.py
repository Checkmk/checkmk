#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import lru_cache
from typing import cast, get_args, override

from pydantic import ConfigDict, TypeAdapter
from typing_extensions import TypeForm


class _HashableArgs[T]:
    """A class to make the arguments of `get_cached_type_adapter` hashable, so they can be used with
    the `lru_cache`. This is necessary because `ConfigDict` does not implement `__hash__`."""

    __slots__ = ("type", "config")

    def __init__(
        self,
        type_: TypeForm[T],
        config: ConfigDict | None = None,
    ) -> None:
        self.type = type_
        self.config = config

    @override
    def __hash__(self) -> int:
        if self.config is None:
            return hash(self.type)
        # The config values are not necessarily hashable, so we only hash the keys. Like for the
        # comparison in __eq__, their order doesn't matter.
        return hash((self.type, frozenset(self.config)))

    @override
    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _HashableArgs)
            and self.type == other.type
            and _ordered_args(self.type) == _ordered_args(other.type)
            and self.config == other.config
        )


def _ordered_args(type_: object) -> tuple[object, ...]:
    """Get the type arguments recursively, keeping their order.

    Unions and literals are equal regardless of the order of their members, but pydantic respects
    the order, e.g. when several members of a union match. So the type alone is not enough as a
    cache key.
    """
    return tuple((arg, _ordered_args(arg)) for arg in get_args(type_))


@lru_cache(maxsize=128)  # arbitrarily chosen, should be ~2x of what EndpointModel.build uses
def _get_type_adapter[T](args: _HashableArgs[T]) -> TypeAdapter[T]:  # type: ignore[misc]
    """Get a TypeAdapter for the given type."""
    # This is only called on a cache miss, and the cache keeps `args` as the key. Replace the
    # caller's config in there by a copy, so that changing the config later, even a nested
    # value, doesn't affect the key. Copying only here avoids copying on every cache hit.
    if args.config is not None:
        args.config = cast("ConfigDict", _copy_containers(args.config))
    # astrein: disable=pydantic-type-adapter
    return TypeAdapter(args.type, config=args.config)


def _copy_containers(value: object) -> object:
    """Copy the nested dicts, lists, tuples and sets of a value, keeping all other values.

    Unlike deepcopy, this keeps values which are only equal to themselves, like functools.partial
    objects or instances of callable classes, so the copy is still equal to the original.
    """
    match value:
        case dict():
            return {key: _copy_containers(item) for key, item in value.items()}
        case list():
            return [_copy_containers(item) for item in value]
        case tuple():
            return tuple(_copy_containers(item) for item in value)
        case set():
            return set(value)
        case _:
            return value


def get_cached_type_adapter[T](
    type_: TypeForm[T], *, config: ConfigDict | None = None
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
