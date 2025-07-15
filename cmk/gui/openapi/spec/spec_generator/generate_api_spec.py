#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This is intended to be used from Bazel from command line to generate the OpenAPI spec
"""

import argparse
import sys
from contextlib import suppress
from pathlib import Path

from cmk.ccc.version import Edition

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


def _import_cre_endpoints() -> None:
    with suppress(Exception):
        from cmk.gui.cre.registration import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
            register as cre_registration,
        )

        cre_registration(Edition.CRE, ignore_duplicate_endpoints=True)


def _import_cee_endpoints() -> None:
    with suppress(Exception):
        from cmk.gui.cee.registration import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
            register as cee_registration,
        )

        cee_registration(Edition.CEE, ignore_duplicate_endpoints=True)


def _import_cce_endpoints() -> None:
    with suppress(Exception):
        from cmk.gui.cce.registration import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
            register as cce_registration,
        )

        cce_registration(Edition.CCE, ignore_duplicate_endpoints=True)


def _import_cme_endpoints() -> None:
    with suppress(Exception):
        from cmk.gui.cme.registration import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
            register as cme_registration,
        )

        cme_registration(Edition.CME, ignore_duplicate_endpoints=True)


def _import_cse_endpoints() -> None:
    with suppress(Exception):
        from cmk.gui.cse.registration import (  # type: ignore[import-not-found, import-untyped, unused-ignore] # pylint: disable=cmk-module-layer-violation
            register as cse_registration,
        )

        cse_registration(Edition.CSE, ignore_duplicate_endpoints=True)


def process_version(args: argparse.Namespace) -> None:
    _import_cre_endpoints()
    _import_cee_endpoints()
    _import_cce_endpoints()
    _import_cme_endpoints()
    _import_cse_endpoints()

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
