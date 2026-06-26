#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Reusable base class for JSON (de-)serialization with a type tag.
"""

import abc
from collections.abc import Mapping
from typing import final, Self, TypedDict


class JsonEnvelope[TParams: Mapping[str, object]](TypedDict):
    """The tagged JSON envelope produced by `JsonSerializable.to_json()`:
    a type tag plus the object's own serialized params."""

    constructor_class: str
    params: TParams


class JsonSerializable[TParams: Mapping[str, object], TContext](abc.ABC):
    """Mixin/ABC giving an object self-contained JSON (de-)serialization.

    Generic over:

    * ``TParams`` -- the params payload. Concrete classes bind it to a
      ``TypedDict`` so that ``serialized_params()`` (construction) and
      ``from_params()`` (access) are type-linked and checked per key.
    * ``TContext`` -- runtime dependencies needed to rebuild an instance that
      are *not* part of the serialized JSON (e.g. a base path or a plugin
      store). Implementations ignore the fields they don't need.

    The ``TParams`` ``TypedDict`` describes the **on-disk JSON shape, not the
    in-memory Python shape**: JSON has no tuples, so tuple-valued fields must be
    typed as ``list``/``Sequence`` and ``serialized_params()`` must normalize
    tuples to lists, so that the single ``TParams`` type is truthful in both
    directions.
    """

    @final
    def to_json(self) -> JsonEnvelope[TParams]:
        return {"constructor_class": type(self).__name__, "params": self.serialized_params()}

    @abc.abstractmethod
    def serialized_params(self) -> TParams:
        """Return the JSON-encodable params for this instance."""

    @classmethod
    @abc.abstractmethod
    def from_params(cls, params: TParams, ctx: TContext) -> Self:
        """Rebuild an instance from `params`, pulling non-serialized
        dependencies from `ctx`."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JsonSerializable):
            return NotImplemented
        return type(self) is type(other) and self.serialized_params() == other.serialized_params()
