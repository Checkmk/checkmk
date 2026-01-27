#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from cmk.product_telemetry.collectors.grafana import remove_grafana_usage_data
from cmk.product_telemetry.exceptions import InvalidTelemetryEndpointError
from cmk.utils.http_proxy_config import EnvironmentProxyConfig, HTTPProxyConfig

DEFAULT_PROXY = EnvironmentProxyConfig()


def transmit_telemetry_data(
    var_dir: Path, logger: logging.Logger, proxy_config: HTTPProxyConfig = DEFAULT_PROXY
) -> None:
    logger.info("Data transmission starts")

    directory = var_dir / "telemetry"

    # Ignored mypy error: it only checks filenames that already match the pattern, so it will never call group() on None
    files = sorted(
        directory.glob("telemetry_[0-9]*.json"),
        key=lambda f: int(re.search(r"telemetry_(\d+)\.json", f.name).group(1)),  # type: ignore[union-attr]
    )

    transmission_results: dict[str, bool] = {}
    for file_path in files:
        successful_response = _transmit_single_telemetry_file(file_path, proxy_config, logger)
        transmission_results[file_path.name] = successful_response
        if successful_response:
            file_path.unlink()

    # Earlier we sorted the files ascending, so the newest is the last one.
    # Now we check if the last file was transmitted successfully to decide whether to delete grafana usage data.
    if files:
        newest_file = files[-1]
        if transmission_results.get(newest_file.name):
            logger.info("Removing Grafana usage data")
            remove_grafana_usage_data(var_dir)


def _transmit_single_telemetry_file(
    file_path: Path, proxy_config: HTTPProxyConfig, logger: logging.Logger
) -> bool:
    logger.info("Tansmitting %s", file_path)

    with file_path.open("r", encoding="utf-8") as f:
        json_data = json.load(f)

    response = requests.post(
        _get_api_url(),
        json=json_data,
        timeout=30,
        proxies=proxy_config.to_requests_proxies(),
    )

    if not response.ok:
        logger.error("Error during transmission: status %s %s", response.status_code, response.text)

    return response.ok


def _get_api_url() -> str:
    domain = os.environ.get("CMK_TELEMETRY_URL", "https://analytics.checkmk.com/upload")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InvalidTelemetryEndpointError
    return domain
