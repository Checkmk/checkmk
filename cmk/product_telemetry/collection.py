#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

import cmk.product_telemetry.collectors.checks as checks_collector
import cmk.product_telemetry.collectors.grafana as grafana_collector
import cmk.product_telemetry.collectors.site_info as site_info_collector
from cmk.product_telemetry.schema import ProductTelemetryPayload


def collect_telemetry_data(var_dir: Path, cmk_config_dir: Path) -> ProductTelemetryPayload:
    site_info = site_info_collector.collect(cmk_config_dir)

    telemetry_data = ProductTelemetryPayload(
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

    return ProductTelemetryPayload.model_validate(telemetry_data)


def store_telemetry_data(data: ProductTelemetryPayload, var_dir: Path) -> None:
    filename = f"telemetry_{data.timestamp}.json"

    directory = var_dir / "telemetry"
    directory.mkdir(parents=True, exist_ok=True)

    with (directory / filename).open("wb") as f:
        f.write(data.model_dump_with_metadata_json())
