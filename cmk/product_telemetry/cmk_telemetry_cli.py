#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from cmk.product_telemetry.collection import (
    collect_telemetry_data,
    store_telemetry_data,
    telemetry_data_storage_path,
)
from cmk.product_telemetry.config import load_telemetry_config
from cmk.product_telemetry.logger import init_logging
from cmk.product_telemetry.schedule import (
    create_next_random_ts,
    create_next_ts,
    get_next_telemetry_run_ts,
    next_telemetry_run_file_path,
    should_run_telemetry_on_schedule,
    store_next_telemetry_run_ts,
)
from cmk.product_telemetry.transmission import transmit_telemetry_data
from cmk.utils import paths


@dataclass(frozen=True, kw_only=True)
class ProductTelemetryRequest:
    collect: bool = False
    store: bool = False
    upload: bool = False
    schedule: bool = False


def main(args: Sequence[str]) -> int:
    request = parse_args(args)
    logger = init_logging(paths.log_dir)
    now = datetime.now()
    config = load_telemetry_config(logger)
    next_run_file_path = next_telemetry_run_file_path(paths.var_dir)

    try:
        if request.schedule:
            if not config.enabled:
                return 0

            # If this is the first run after product telemetry being enabled,
            # we need to create a random next timestamp somewhere in the next 30 days and then exit.
            if not get_next_telemetry_run_ts(next_run_file_path):
                next_scheduled_run_at = create_next_random_ts(now)
                logger.info(
                    "First scheduled execution, planning the next execution at %s",
                    next_scheduled_run_at,
                )
                store_next_telemetry_run_ts(next_run_file_path, next_scheduled_run_at)
                return 0

            if not should_run_telemetry_on_schedule(paths.var_dir, now):
                return 0

            logger.info("Scheduled run starts")

        if request.collect:
            data = collect_telemetry_data(
                paths.var_dir,
                paths.check_mk_config_dir,
                paths.omd_root,
                logger,
            )
            sys.stdout.write(data.model_dump_with_metadata_json(indent=2).decode("utf-8") + "\n")
            sys.stdout.flush()

            if request.store:
                store_telemetry_data(data, paths.var_dir)

        if request.upload:
            transmit_telemetry_data(paths.var_dir, logger, proxy_config=config.proxy_config)

        if request.schedule:
            next_scheduled_run_at = create_next_ts(now)
            logger.info("Planning the next execution at %s", next_scheduled_run_at)
            store_next_telemetry_run_ts(next_run_file_path, next_scheduled_run_at)

    except Exception as e:
        sys.stderr.write(f"cmk-telemetry: {e}\n")
        logger.exception("Unexpected error")
        return -1

    logger.info("Successfully ran")

    return 0


def parse_args(args: Sequence[str]) -> ProductTelemetryRequest:
    storage_directory = telemetry_data_storage_path(paths.var_dir).absolute()
    parser = argparse.ArgumentParser(
        prog="cmk-telemetry",
        usage="cmk-telemetry [--collection | --upload | --dry-run]",
        description=(
            "Collect and send telemetry data. "
            f"You can collect and store data locally in `{storage_directory}`, "
            "upload telemetry files, "
            "or display telemetry data in a dry-run mode."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--collection",
        action="store_true",
        help=f"Collect telemetry data and store it locally in `{storage_directory}`.",
    )
    group.add_argument(
        "--upload",
        action="store_true",
        help=f"Send local telemetry data files from `{storage_directory}`.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show telemetry data in output without storing or sending.",
    )
    group.add_argument(
        "--cron",
        action="store_true",
        help="Used by the crontab to trigger the collection, storing and transmission on a regular schedule.",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.collection:
        return ProductTelemetryRequest(collect=True, store=True)
    elif parsed_args.upload:
        return ProductTelemetryRequest(upload=True)
    elif parsed_args.dry_run:
        return ProductTelemetryRequest(collect=True)
    elif parsed_args.cron:
        return ProductTelemetryRequest(collect=True, store=True, upload=True, schedule=True)
    return ProductTelemetryRequest(collect=True, store=True, upload=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
