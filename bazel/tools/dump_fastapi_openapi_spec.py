#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class _OpenApiApp(Protocol):
    def openapi(self) -> object: ...


def _load_factory(spec: str) -> Callable[[], _OpenApiApp]:
    module_name, separator, factory_name = spec.partition(":")
    if not (separator and module_name and factory_name):
        raise ValueError(f"expected <module>:<factory>, got {spec!r}")
    factory: Callable[[], _OpenApiApp] = getattr(importlib.import_module(module_name), factory_name)
    return factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump the OpenAPI schema of a FastAPI app")
    parser.add_argument("--app", required=True, help="app factory as <module>:<factory>")
    parser.add_argument("--out", required=True, type=Path, help="file to write the schema to")
    args = parser.parse_args()

    app = _load_factory(args.app)()
    args.out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
