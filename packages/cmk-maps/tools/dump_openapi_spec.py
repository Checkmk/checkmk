#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Dump the Maps daemon's OpenAPI schema, for generating the SPA's daemon types.

Goes through :func:`cmk.maps.backend.app.create_app` rather than the runtime
entry point on purpose: this runs as a build action with no OMD site around it,
and importing the runtime module would configure logging and install tracing
instrumentation as a side effect. ``tests/unit/test_app_factory.py`` pins that,
and pins that the schema does not vary with the environment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cmk.maps.backend.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="file to write the schema to")
    args = parser.parse_args()

    # Sorted keys: a build artifact has to be byte-stable, and neither pydantic's
    # model order nor dict insertion order is a contract we want to depend on.
    args.out.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
