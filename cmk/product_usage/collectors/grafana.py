#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from logging import Logger
from pathlib import Path

import pydantic
from werkzeug.datastructures import Headers

from cmk.ccc import store
from cmk.product_usage.schema import GrafanaUsageData


def store_usage_data(headers: Headers, var_dir: Path, logger: Logger) -> None:
    try:
        # If there is no Grafana usage header, we stop processing.
        if not headers.get("X-Grafana-Org-Id"):
            return

        grafana_file_path = _grafana_usage_file_path(var_dir)
        # If we have already recorded Grafana usage, we stop processing.
        if grafana_file_path.exists():
            return

        data: GrafanaUsageData = GrafanaUsageData(
            is_used=True,
            version=_grafana_version(headers) or "unknown",
            is_grafana_cloud=_is_grafana_cloud(headers),
        )

        grafana_file_path.parent.mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(grafana_file_path, data.model_dump_json())
    except Exception:
        logger.error("Store Grafana usage failed", exc_info=True)


def _grafana_usage_file_path(var_dir: Path) -> Path:
    return var_dir / "product_usage" / "grafana_usage.json"


def _grafana_version(headers: Headers) -> str | None:
    user_agent = headers.get("User-Agent", "")
    match = re.search(r"Grafana/(.*?)$", user_agent)
    return match.group(1) if match else None


def _is_grafana_cloud(headers: Headers) -> bool:
    if referer := headers.get("X-Grafana-Referer"):
        referer_url = pydantic.HttpUrl(referer)
        return referer_url.host is not None and referer_url.host.endswith(".grafana.net")
    return False


def remove_grafana_usage_data(var_dir: Path) -> None:
    grafana_fp = _grafana_usage_file_path(var_dir)
    if grafana_fp.exists():
        grafana_fp.unlink()


def collect(var_dir: Path) -> GrafanaUsageData | None:
    grafana_fp = _grafana_usage_file_path(var_dir)

    if not grafana_fp.exists():
        return None

    return GrafanaUsageData.model_validate_json(grafana_fp.read_text())
