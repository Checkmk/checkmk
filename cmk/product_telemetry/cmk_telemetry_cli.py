#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.product_telemetry.collection import collect_telemetry_data, store_telemetry_data
from cmk.product_telemetry.transmission import transmit_telemetry_data
from cmk.utils import paths


@dataclass(frozen=True, kw_only=True)
class ProductTelemetryRequest:
    collect: bool = False
    store: bool = False
    upload: bool = False


def main(args: Sequence[str]) -> int:
    request = parse_args(args)

    try:
        if request.collect:
            data = collect_telemetry_data(paths.var_dir, paths.check_mk_config_dir, paths.omd_root)
            sys.stdout.write(data.model_dump_with_metadata_json().decode("utf-8") + "\n")
            sys.stdout.flush()

            if request.store:
                store_telemetry_data(data, paths.var_dir)

        if request.upload:
            transmit_telemetry_data(paths.var_dir)

    except Exception as e:
        sys.stderr.write(f"cmk-telemetry: {e}\n")
        return -1

    return 0


def parse_args(args: Sequence[str]) -> ProductTelemetryRequest:
    parser = argparse.ArgumentParser(
        prog="cmk-telemetry",
        usage="cmk-telemetry [--collection | --upload | --dry-run]",
        description="Collect and send telemetry data. You can collect and store data locally, upload telemetry files, or display telemetry data in a dry-run mode.",
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--collection",
        action="store_true",
        help="Collect telemetry data and store it locally.",
    )
    group.add_argument(
        "--upload",
        action="store_true",
        help="Send local telemetry data files.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show telemetry data in output without storing or sending.",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.collection:
        return ProductTelemetryRequest(collect=True, store=True)
    elif parsed_args.upload:
        return ProductTelemetryRequest(upload=True)
    elif parsed_args.dry_run:
        return ProductTelemetryRequest(collect=True)
    return ProductTelemetryRequest(collect=True, store=True, upload=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
