#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import json
from collections.abc import Mapping, Sequence
from typing import assert_never

from ._model import RenderingFailure


def _png_result_to_json(result: bytes | RenderingFailure) -> Mapping[str, str]:
    match result:
        case bytes():
            return {"png": base64.b64encode(result).decode("ascii")}
        case RenderingFailure():
            return {"failure": result.message}
        case other:
            assert_never(other)


def pngs_to_json(results: Sequence[bytes | RenderingFailure]) -> str:
    return json.dumps([_png_result_to_json(result) for result in results])


def _ensure_type[T](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
    return value


def _png_result(raw: object) -> bytes | RenderingFailure:
    fields = _ensure_type(raw, dict)
    if "failure" in fields:
        return RenderingFailure(_ensure_type(fields["failure"], str))
    return base64.b64decode(_ensure_type(fields["png"], str))


def pngs_from_json(text: str) -> Sequence[bytes | RenderingFailure]:
    return [_png_result(raw) for raw in _ensure_type(json.loads(text), list)]
