#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dumps the OpenAPI 3.1 document openapi-typescript reads for a FastAPI app.

openapi-typescript does not read a stream's `itemSchema`. The document describes a streamed
item as the response `schema`, with JSON-encoded fields as the value they decode to, since
that is what a client of the stream gets to see.
"""

import argparse
import copy
import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol


class _OpenApiApp(Protocol):
    def openapi(self) -> Mapping[str, object]: ...


def _load_factory(spec: str) -> Callable[[], _OpenApiApp]:
    module_name, separator, factory_name = spec.partition(":")
    if not (separator and module_name and factory_name):
        raise ValueError(f"expected <module>:<factory>, got {spec!r}")
    factory: Callable[[], _OpenApiApp] = getattr(importlib.import_module(module_name), factory_name)
    return factory


def typescript_view(spec: Mapping[str, object]) -> dict[str, object]:
    view = copy.deepcopy(dict(spec))
    for path, path_item in _fields(view.get("paths")).items():
        for method, operation in _fields(path_item).items():
            for status, response in _fields(_fields(operation).get("responses")).items():
                for media_type, media in _fields(_fields(response).get("content")).items():
                    _move_item_schema(
                        _fields(media), f"{method.upper()} {path} {status} {media_type}"
                    )
    view["openapi"] = "3.1.0"
    return view


def _fields(node: object) -> dict[str, object]:
    return node if isinstance(node, dict) else {}


def _move_item_schema(media: dict[str, object], at: str) -> None:
    if "itemSchema" not in media:
        return
    if "schema" in media:
        raise ValueError(f"{at} has both a schema and an itemSchema")
    media["schema"] = _json_decoded(media.pop("itemSchema"))


def _json_decoded(schema: object) -> object:
    if isinstance(schema, dict):
        if schema.get("contentMediaType") == "application/json" and "contentSchema" in schema:
            return schema["contentSchema"]
        return {key: _json_decoded(value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_json_decoded(value) for value in schema]
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump the OpenAPI schema of a FastAPI app")
    parser.add_argument("--app", required=True, help="app factory as <module>:<factory>")
    parser.add_argument("--out", required=True, type=Path, help="file to write the schema to")
    args = parser.parse_args()

    view = typescript_view(_load_factory(args.app)().openapi())
    args.out.write_text(json.dumps(view, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
