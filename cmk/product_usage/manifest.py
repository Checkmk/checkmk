#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Write the manifest of the product usage analytics data as a JSON schema"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pydantic_core

from cmk.product_usage.schema import ProductUsagePayload


def build_manifest() -> dict[str, object]:
    return {
        "title": "Checkmk product usage analytics",
        "description": (
            "All data points collected when the product usage analytics feature is enabled."
        ),
        **ProductUsagePayload.model_json_schema_with_metadata(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path of the manifest file to write")
    args = parser.parse_args(argv)
    args.output.write_bytes(pydantic_core.to_json(build_manifest(), indent=2) + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
