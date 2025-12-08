#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from cmk.product_telemetry.collectors.grafana import remove_grafana_usage_data
from cmk.product_telemetry.exceptions import InvalidTelemetryEndpointError


def transmit_telemetry_data(var_dir: Path) -> None:
    # TODO: Logging for failed transmissions. E.g. timestamp, filename, success/failure, status code?
    directory = var_dir / "telemetry"

    # Ignored mypy error: it only checks filenames that already match the pattern, so it will never call group() on None
    files = sorted(
        directory.glob("telemetry_[0-9]*.json"),
        key=lambda f: int(re.search(r"telemetry_(\d+)\.json", f.name).group(1)),  # type: ignore[union-attr]
    )

    transmission_results: dict[str, bool] = {}
    for file_path in files:
        successful_response = _transmit_single_telemetry_file(file_path)
        transmission_results[file_path.name] = successful_response
        if successful_response:
            file_path.unlink()

    # Earlier we sorted the files ascending, so the newest is the last one.
    # Now we check if the last file was transmitted successfully to decide whether to delete grafana usage data.
    if files:
        newest_file = files[-1]
        if transmission_results.get(newest_file.name):
            remove_grafana_usage_data(var_dir)


def _transmit_single_telemetry_file(file_path: Path) -> bool:
    with file_path.open("r", encoding="utf-8") as f:
        json_data = json.load(f)

    response = requests.post(_get_api_url(), json=json_data, timeout=30)
    return response.ok


def _get_api_url() -> str:
    domain = os.environ.get("CMK_TELEMETRY_URL", "https://telemetry.checkmk.com/upload")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InvalidTelemetryEndpointError
    return domain
