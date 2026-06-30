#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, get_args, get_origin

from werkzeug.http import parse_options_header


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

    # Split off any media type parameters (e.g. ``application/json; charset="utf-8"``) so the type
    # matches, and honor the declared charset when decoding.
    media_type, options = parse_options_header(content_type)
    if media_type.lower() == "application/json":
        if charset := options.get("charset"):
            try:
                return json.loads(body.decode(charset))
            except (LookupError, UnicodeDecodeError) as exc:
                # LookupError: unknown charset; UnicodeDecodeError: body invalid for that charset.
                raise ValueError(
                    f"Cannot decode request body using charset {charset!r}: {exc}"
                ) from exc
        # No charset given: let json detect it
        return json.loads(body)

    raise ValueError("Unsupported content type: %s" % content_type)


__all__ = [
    "ContentTypeConverter",
    "get_converter_annotation",
    "convert_request_body",
]
