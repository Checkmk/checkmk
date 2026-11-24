#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Sequence
from pathlib import Path

import cmk.product_usage.collectors.agent_updater as agent_updater_collector
import cmk.product_usage.collectors.audit_log as audit_log_collector
import cmk.product_usage.collectors.checks as checks_collector
import cmk.product_usage.collectors.distributed_monitoring as distributed_monitoring_collector
import cmk.product_usage.collectors.grafana as grafana_collector
import cmk.product_usage.collectors.host_services as host_services_collector
import cmk.product_usage.collectors.inventory as inventory_collector
import cmk.product_usage.collectors.languages as languages_collector
import cmk.product_usage.collectors.site_info as site_info_collector
import cmk.product_usage.collectors.user_stats as user_stats_collector
import cmk.product_usage.collectors.users as users_collector
from cmk.ccc.site import omd_site
from cmk.product_usage.collectors.user_store import load_users_with_profiles, StoredUser
from cmk.product_usage.schema import (
    AgentUpdaterData,
    AuditLog,
    CloudTrialPayload,
    DistributedMonitoring,
    Languages,
    ProductUsagePayload,
    UserCount,
    UsersData,
)


def collect_data(
    var_dir: Path,
    cmk_config_dir: Path,
    default_config_dir: Path,
    omd_root: Path,
    locale_dir: Path,
    logger: logging.Logger,
) -> ProductUsagePayload:
    logger.info("Collection starts")

    now = int(time.time())
    site_info = site_info_collector.collect(cmk_config_dir, var_dir, omd_root)
    users = _load_users(default_config_dir, var_dir, logger)

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
        users=_collect_users(users, default_config_dir, now, logger),
        inventory=inventory_collector.collect(),
        distributed_monitoring=_collect_distributed_monitoring(
            default_config_dir, cmk_config_dir, logger
        ),
        languages=_collect_languages(users, default_config_dir, locale_dir, now, logger),
        grafana=grafana_collector.collect(var_dir),
        agent_updater=_collect_agent_updater(omd_root, logger),
    )


def _collect_agent_updater(omd_root: Path, logger: logging.Logger) -> AgentUpdaterData | None:
    """Collect the agent updater usage without letting its failure lose the payload"""
    try:
        return agent_updater_collector.collect(omd_root, omd_site(), logger)
    except Exception:
        logger.exception("Could not collect the agent updater usage, sending no counts")
        return None


def _collect_distributed_monitoring(
    default_config_dir: Path, cmk_config_dir: Path, logger: logging.Logger
) -> DistributedMonitoring | None:
    try:
        return distributed_monitoring_collector.collect(
            default_config_dir=default_config_dir, cmk_config_dir=cmk_config_dir
        )
    except Exception:
        logger.exception("Could not determine the distributed monitoring role, sending none")
        return None


def _load_users(
    default_config_dir: Path, var_dir: Path, logger: logging.Logger
) -> Sequence[StoredUser] | None:
    """Read the users once for the user counts and the languages, both are lost if this fails"""
    try:
        return load_users_with_profiles(default_config_dir, var_dir / "web")
    except Exception:
        logger.exception("Could not read the users, sending no user counts and no languages")
        return None


def _collect_users(
    users: Sequence[StoredUser] | None,
    default_config_dir: Path,
    now: int,
    logger: logging.Logger,
) -> UsersData | None:
    if users is None:
        return None
    try:
        return user_stats_collector.collect(users, default_config_dir, now)
    except Exception:
        logger.exception("Could not count the users, sending no user counts")
        return None


def _collect_languages(
    users: Sequence[StoredUser] | None,
    default_config_dir: Path,
    locale_dir: Path,
    now: int,
    logger: logging.Logger,
) -> Languages | None:
    if users is None:
        return None
    try:
        return languages_collector.collect(
            users, default_config_dir=default_config_dir, locale_dir=locale_dir, now=now
        )
    except Exception:
        logger.exception("Could not collect the languages, sending no languages")
        return None


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
