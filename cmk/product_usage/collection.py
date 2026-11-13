#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from pathlib import Path

import cmk.product_usage.collectors.audit_log as audit_log_collector
import cmk.product_usage.collectors.checks as checks_collector
import cmk.product_usage.collectors.grafana as grafana_collector
import cmk.product_usage.collectors.host_services as host_services_collector
import cmk.product_usage.collectors.inventory as inventory_collector
import cmk.product_usage.collectors.site_info as site_info_collector
import cmk.product_usage.collectors.user_stats as user_stats_collector
import cmk.product_usage.collectors.users as users_collector
from cmk.product_usage.schema import (
    AuditLog,
    CloudTrialPayload,
    ProductUsagePayload,
    UserCount,
)


def collect_data(
    var_dir: Path,
    cmk_config_dir: Path,
    default_config_dir: Path,
    omd_root: Path,
    logger: logging.Logger,
) -> ProductUsagePayload:
    logger.info("Collection starts")

    now = int(time.time())
    site_info = site_info_collector.collect(cmk_config_dir, var_dir, omd_root)

    return ProductUsagePayload(
        timestamp=now,
        id=site_info.id,
        count_hosts=site_info.count_hosts,
        count_services=site_info.count_services,
        count_folders=site_info.count_folders,
        edition=site_info.edition,
        cmk_version=site_info.cmk_version,
        os=site_info.os,
        checks=checks_collector.collect(),
        users=user_stats_collector.collect(default_config_dir, var_dir / "web", now),
        inventory=inventory_collector.collect(),
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


# The users with which the Cloud platform acts on a trial site
_CLOUD_PLATFORM_USER_IDS = frozenset({"api_user", "agent_registration"})


def collect_cloud_trial_data(
    product_usage: ProductUsagePayload,
    *,
    var_dir: Path,
    default_config_dir: Path,
    logger: logging.Logger,
    read_services_per_host: host_services_collector.ServicesPerHostReader = (
        host_services_collector.read_services_per_host
    ),
) -> CloudTrialPayload:
    return CloudTrialPayload(
        **dict(product_usage),
        count_users=_collect_count_users(default_config_dir, logger),
        audit_log=_collect_audit_log(var_dir, default_config_dir, logger),
        count_hosts_default_services_only=_count_hosts_with_only_default_services(
            read_services_per_host, logger
        ),
    )


def _collect_count_users(default_config_dir: Path, logger: logging.Logger) -> UserCount | None:
    try:
        return users_collector.collect(default_config_dir)
    except Exception:
        logger.exception("Could not count the users, sending no user counts")
        return None


def _collect_audit_log(
    var_dir: Path, default_config_dir: Path, logger: logging.Logger
) -> AuditLog | None:
    try:
        return audit_log_collector.collect(
            var_dir, default_config_dir, platform_user_ids=_CLOUD_PLATFORM_USER_IDS
        )
    except Exception:
        logger.exception("Could not collect the audit log, sending no audit log")
        return None


def _count_hosts_with_only_default_services(
    read_services_per_host: host_services_collector.ServicesPerHostReader, logger: logging.Logger
) -> int | None:
    try:
        return host_services_collector.collect(read_services_per_host())
    except Exception:
        logger.exception("Could not count the hosts with default services only, sending no count")
        return None
