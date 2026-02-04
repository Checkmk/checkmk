#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from pathlib import Path

import cmk.product_usage.collectors.checks as checks_collector
import cmk.product_usage.collectors.grafana as grafana_collector
import cmk.product_usage.collectors.site_info as site_info_collector
from cmk.product_usage.schema import ProductUsagePayload


def collect_data(
    var_dir: Path, cmk_config_dir: Path, omd_root: Path, logger: logging.Logger
) -> ProductUsagePayload:
    logger.info("Collection starts")

    site_info = site_info_collector.collect(cmk_config_dir, var_dir, omd_root)

    return ProductUsagePayload(
        timestamp=int(time.time()),
        id=site_info.id,
        count_hosts=site_info.count_hosts,
        count_services=site_info.count_services,
        count_folders=site_info.count_folders,
        edition=site_info.edition,
        cmk_version=site_info.cmk_version,
        checks=checks_collector.collect(),
        grafana=grafana_collector.collect(var_dir),
    )


def store_data(data: ProductUsagePayload, var_dir: Path) -> None:
    filename = f"product_usage_{data.timestamp}.json"

    directory = data_storage_path(var_dir)
    directory.mkdir(parents=True, exist_ok=True)

    with (directory / filename).open("wb") as f:
        f.write(data.model_dump_with_metadata_json())


def data_storage_path(var_dir: Path) -> Path:
    return var_dir / "product_usage"
