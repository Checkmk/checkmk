#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

# There are two variants, because no single type is both safe and convenient.
#
# JsonSerializable is for values we hand to json.dumps() ourselves. Its only containers are dict
# and list, which json.dumps() accepts, so mypy rejects any type that would make it fail. Only
# circular references still fail, which no type can rule out. The price: dict and list are
# invariant, so e.g. a dict[str, str] or a list[dict[str, str]] is no JsonSerializable, and such
# values need a JsonSerializable annotation where they are built.
type JsonSerializable = (
    dict[str, JsonSerializable] | list[JsonSerializable] | str | int | float | bool | None
)

# JsonPayload is for the json= parameter of requests, whose own (private) type for it has the
# same shape. Mapping and Sequence are covariant, so e.g. a dict[str, str] or a
# list[dict[str, JsonPayload]] is a JsonPayload, too, and so is every JsonSerializable. The
# price: bytes (a Sequence[int]), range, deque or a MappingProxyType are JsonPayloads as well,
# although json.dumps() rejects them. That costs nothing for requests, which accepts them in its
# signature anyway, but don't use JsonPayload for values we serialize ourselves.
type JsonPayload = (
    Mapping[str, JsonPayload] | Sequence[JsonPayload] | str | int | float | bool | None
)
