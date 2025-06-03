#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This is intended to be used from Bazel from command line to generate the OpenAPI spec
"""

import argparse
import sys
from pathlib import Path

from cmk.gui.openapi.framework.api_config import APIConfig, APIVersion
from cmk.gui.openapi.spec.spec_generator._core import _make_spec, populate_spec


def build_yaml_spec(output_file: Path, version: APIVersion = APIVersion.V1) -> None:
    spec = _make_spec(version)
    populate_spec(version, spec, "doc", set(), "checkmk")

    c = spec.to_yaml()

    Path(output_file).write_text(c)


def list_versions(args: argparse.Namespace) -> None:
    released_versions = map(str, APIConfig.get_released_versions())
    separator = ", " if args.csv else "\n"

    sys.stdout.write(f"{separator.join(released_versions)}\n")


def process_version(args: argparse.Namespace) -> None:
    try:
        from cmk.gui.cce.registration import (  # pylint: disable=cmk-module-layer-violation
            _openapi_registration as cce_registration,
        )
        from cmk.gui.cee.registration import (  # pylint: disable=cmk-module-layer-violation
            _openapi_registration as cee_registration,
        )
        from cmk.gui.cme.registration import (  # pylint: disable=cmk-module-layer-violation
            _openapi_registration as cme_registration,
        )
        from cmk.gui.cre.registration import (  # pylint: disable=cmk-module-layer-violation
            _openapi_registration as cre_registration,
        )
        from cmk.gui.cse.registration import (  # pylint: disable=cmk-module-layer-violation
            _openapi_registration as cse_registration,
        )

        cre_registration(ignore_duplicates=True)
        cce_registration(ignore_duplicates=True)
        cee_registration(ignore_duplicates=True)
        cme_registration(ignore_duplicates=True)
        cse_registration(ignore_duplicates=True)

    finally:
        version = APIVersion.from_string(args.version)

        build_yaml_spec(args.out, version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(help="Available commands")

    versions_parser = subparsers.add_parser("list", help="List released versions")
    versions_parser.add_argument(
        "--csv",
        help="Print versions as comma separated values",
        required=False,
        action="store_true",
    )
    versions_parser.set_defaults(callback=list_versions)

    process_parser = subparsers.add_parser("generate", help="Generate spec for specific version")
    process_parser.add_argument("--version", help="Must be a published versions", required=True)
    process_parser.add_argument("--out", help="Target file", required=True)
    process_parser.set_defaults(callback=process_version)

    args = parser.parse_args()

    if hasattr(args, "callback"):
        args.callback(args)
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)
