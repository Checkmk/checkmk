#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, get_args, get_origin


@dataclass(slots=True, frozen=True)
class ContentTypeConverter:
    """Annotation type to specify a custom content type converter.

    The function must accept two arguments: the body as bytes and the content type as a string.
    The returned value can be of any type and will be passed into the normal pydantic validation."""

    function: Callable[[bytes, str], object]


def get_converter_annotation(t: type) -> ContentTypeConverter | None:
    """Return the first `ContentTypeConverter` annotation for the given type.

    This function only looks at the outermost type and does not recurse into nested types.
    Content Type annotations are expected to be used with `Annotated` as the outermost type.
    """
    if get_origin(t) is Annotated:
        for annotation in get_args(t):
            if isinstance(annotation, ContentTypeConverter):
                return annotation

    return None


def convert_request_body(body_model: type, content_type: str, body: bytes) -> object:
    """Convert the `body` into the correct type based on the requests `content_type`.

    In most cases, this means decoding a JSON body into a dict. A custom converter can be specified
    using the `ContentTypeConverter` annotation on the `body_model`."""
    if converter := get_converter_annotation(body_model):
        # a custom converter function is defined
        return converter.function(body, content_type)

    if content_type == "application/json":
        # default to JSON decoding
        return json.loads(body)

    raise Exception("Unsupported content type: %s" % content_type)


__all__ = [
    "ContentTypeConverter",
    "get_converter_annotation",
    "convert_request_body",
]
