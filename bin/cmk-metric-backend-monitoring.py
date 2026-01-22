#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path

from clickhouse_connect.driver.exceptions import ClickHouseError

from cmk.metric_backend import monitor
from cmk.metric_backend.client import ClickHouseClient, make_raw_read_only_client
from cmk.metric_backend.config import ConfigMetricBackendSelfHosted
from cmk.utils.licensing.usage import (
    get_license_usage_report_file_path,
    load_raw_license_usage_report,
    LocalLicenseUsageHistory,
)


def main() -> int:
    site_id = os.environ["OMD_SITE"]
    config = monitor.get_config_if_self_hosted(Path(os.environ["OMD_ROOT"]))
    if not config:
        return 0

    request = monitor.make_ping_section(site_id, config)
    sys.stdout.write("<<<metric_backend_omd_ping:sep(0)>>>\n")
    sys.stdout.write(request.model_dump_json() + "\n")

    license_usage = _make_license_usage(site_id, config)
    sys.stdout.write("<<<metric_backend_omd_license_usage:sep(0)>>>\n")
    sys.stdout.write(license_usage.model_dump_json() + "\n")

    return 0


def _make_license_usage(
    site_id: str,
    config: ConfigMetricBackendSelfHosted,
) -> monitor.LicenseUsage:
    try:
        client = ClickHouseClient(make_raw_read_only_client(config))
        number_of_active_series_now = client.active_series_count()
    except ClickHouseError:
        number_of_active_series_now = None

    license_usage_history = LocalLicenseUsageHistory.parse(
        load_raw_license_usage_report(get_license_usage_report_file_path())
    )

    return monitor.LicenseUsage(
        site_id=site_id,
        current_active_series_count=number_of_active_series_now,
        last_reported_active_series_count=last_license_usage_sample.num_active_metric_series
        if (last_license_usage_sample := license_usage_history.last)
        else None,
    )


if __name__ == "__main__":
    sys.exit(main())
