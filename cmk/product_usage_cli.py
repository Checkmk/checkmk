#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from cmk.base.app import make_app
from cmk.base.config import load
from cmk.ccc.version import edition
from cmk.product_usage.collection import (
    collect_data,
    data_storage_path,
    store_data,
)
from cmk.product_usage.config import get_proxy_config, load_product_usage_config, ProductUsageConfig
from cmk.product_usage.logger import init_logging
from cmk.product_usage.schedule import (
    create_next_random_ts,
    create_next_ts,
    get_next_run_ts,
    next_run_file_path,
    should_run_collection_on_schedule,
    store_next_run_ts,
)
from cmk.product_usage.transmission import transmit_data
from cmk.utils import paths


@dataclass(frozen=True, kw_only=True)
class ProductUsageRequest:
    collect: bool = False
    store: bool = False
    upload: bool = False
    schedule: bool = False


def load_config(logger: logging.Logger) -> ProductUsageConfig:
    base_config = load(
        discovery_rulesets=(),
        get_builtin_host_labels=make_app(edition(paths.omd_root)).get_builtin_host_labels,
    )

    config = load_product_usage_config(paths.default_config_dir, logger)

    proxy_config = get_proxy_config(
        proxy_setting=config.proxy_setting,
        global_proxies=base_config.loaded_config.http_proxies,
    )

    return ProductUsageConfig(
        enabled=config.enabled == "enabled",
        state=config.enabled,
        proxy_config=proxy_config,
    )


def main(args: Sequence[str]) -> int:
    request = parse_args(args)
    logger = init_logging(paths.log_dir)
    now = datetime.now()
    config = load_config(logger)
    next_run_fp = next_run_file_path(paths.var_dir)

    try:
        if request.schedule:
            if not config.enabled:
                return 0

            # If this is the first run after product usage analytics being enabled,
            # we need to create a random next timestamp somewhere in the next 30 days and then exit.
            if not get_next_run_ts(next_run_fp):
                next_scheduled_run_at = create_next_random_ts(now)
                logger.info(
                    "First scheduled execution, planning the next execution at %s",
                    next_scheduled_run_at,
                )
                store_next_run_ts(next_run_fp, next_scheduled_run_at)
                return 0

            if not should_run_collection_on_schedule(paths.var_dir, now):
                return 0

            logger.info("Scheduled run starts")

        if request.collect:
            data = collect_data(
                paths.var_dir,
                paths.check_mk_config_dir,
                paths.omd_root,
                logger,
            )
            sys.stdout.write(data.model_dump_with_metadata_json(indent=2).decode("utf-8") + "\n")
            sys.stdout.flush()

            if request.store:
                store_data(data, paths.var_dir)

        if request.upload:
            transmit_data(paths.var_dir, logger, proxy_config=config.proxy_config)

        if request.schedule:
            next_scheduled_run_at = create_next_ts(now)
            logger.info("Planning the next execution at %s", next_scheduled_run_at)
            store_next_run_ts(next_run_fp, next_scheduled_run_at)

    except Exception as e:
        sys.stderr.write(f"cmk-product-usage: {e}\n")
        logger.exception("Unexpected error")
        return -1

    logger.info("Successfully ran")

    return 0


def parse_args(args: Sequence[str]) -> ProductUsageRequest:
    storage_directory = data_storage_path(paths.var_dir).absolute()
    parser = argparse.ArgumentParser(
        prog="cmk-product-usage",
        usage="cmk-product-usage [--collection | --upload | --dry-run]",
        description=(
            "Collect and send product usage data. "
            f"You can collect and store data locally in `{storage_directory}`, "
            "upload product usage files, "
            "or display product usage data in a dry-run mode."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--collection",
        action="store_true",
        help=f"Collect product usage data and store it locally in `{storage_directory}`.",
    )
    group.add_argument(
        "--upload",
        action="store_true",
        help=f"Send local product usage data files from `{storage_directory}`.",
    )
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show product usage data in output without storing or sending.",
    )
    group.add_argument(
        "--cron",
        action="store_true",
        help="Used by the crontab to trigger the collection, storing and transmission on a regular schedule.",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.collection:
        return ProductUsageRequest(collect=True, store=True)
    elif parsed_args.upload:
        return ProductUsageRequest(upload=True)
    elif parsed_args.dry_run:
        return ProductUsageRequest(collect=True)
    elif parsed_args.cron:
        return ProductUsageRequest(collect=True, store=True, upload=True, schedule=True)
    return ProductUsageRequest(collect=True, store=True, upload=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
