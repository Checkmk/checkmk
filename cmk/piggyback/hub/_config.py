#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import os
import time
from collections.abc import Mapping
from logging import Logger
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, PlainValidator

from cmk.ccc.hostaddress import HostName
from cmk.messaging import Channel, Connection, QueueName, RoutingKey
from cmk.messaging.rabbitmq import rabbitmqctl_process

from ._paths import RELATIVE_CONFIG_PATH
from ._utils import APP_NAME

CONFIG_ROUTE = RoutingKey("config")
CONFIG_QUEUE = QueueName("config")
DEFAULT_VHOST_NAME = "/"
DEFAULT_CUSTOMER = "provider"


AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


type HostLocations = Mapping[AnnotatedHostName, str]
"""A map of host names to the sites they are monitored on."""


class ConfigType(enum.Enum):
    ONESHOT = enum.auto()
    PERSISTED = enum.auto()


class PiggybackHubConfig(BaseModel):
    type: ConfigType
    locations: HostLocations


class _PersistedPiggybackHubConfig(BaseModel):
    locations: Mapping[AnnotatedHostName, str] = {}


def save_config(omd_root: Path, config: PiggybackHubConfig) -> None:
    persisted = _PersistedPiggybackHubConfig(locations=config.locations)
    path = omd_root / RELATIVE_CONFIG_PATH
    path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    tmp_path = path.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(f"{persisted.model_dump_json()}\n")
    tmp_path.rename(path)


def load_config(omd_root: Path) -> PiggybackHubConfig:
    try:
        locations = _PersistedPiggybackHubConfig.model_validate_json(
            (omd_root / RELATIVE_CONFIG_PATH).read_text()
        ).locations
    except FileNotFoundError:
        locations = {}
    return PiggybackHubConfig(type=ConfigType.PERSISTED, locations=locations)


def publish_persisted_locations(
    logger: Logger,
    destination_site: str,
    locations: HostLocations,
    omd_root: Path,
    omd_site: str,
    customer: str = DEFAULT_CUSTOMER,
) -> None:
    """Publish host locations for continuous distribution of piggyback data.

    Args:
        destination_site: The site to receive the instruction to send piggyback data
        locations: A mapping of host names to the sites they are monitored on.
        omd_root: The path to the OMD root directory of this site.
        omd_site: The name of this OMD site
        customer: The customer (vhost) to publish to, or None for the provider ("/") vhost
    """
    config = PiggybackHubConfig(type=ConfigType.PERSISTED, locations=locations)
    _publish_config(logger, destination_site, config, omd_root, omd_site, customer)


def publish_one_shot_locations(
    logger: Logger,
    destination_site: str,
    locations: HostLocations,
    omd_root: Path,
    omd_site: str,
) -> None:
    """Publish host locations for one-shot distribution of piggyback data.

    Args:
        destination_site: The site to receive the instruction to send piggyback data
        locations: A mapping of host names to the sites they are monitored on.
        omd_root: The path to the OMD root directory of this site.
        omd_site: The name of this OMD site
    """
    config = PiggybackHubConfig(type=ConfigType.ONESHOT, locations=locations)
    # one-shot should be communicated only from central site to remote sites (customer 'provider')
    _publish_config(logger, destination_site, config, omd_root, omd_site, customer=DEFAULT_CUSTOMER)


def _wait_config_queue_ready(logger: Logger, channel: Channel[PiggybackHubConfig]) -> bool:
    """
    Wait until the config queue exists (max 1 second), to avoid publishing into non-existing queues.
    This could happen when, after rabbitmq definitions are loaded (stop_app -> start_app),
    RabbitMQ has not yet really created/activated this queue, created runtime.
    """
    queue_name = channel.make_queue_name(CONFIG_QUEUE)

    def _check_queue_exists() -> bool:
        popen = rabbitmqctl_process(
            ("list_queues", "--quiet", "--no-table-headers", "name"), wait=True
        )
        if popen.stdout and (lines := popen.stdout.readlines()):
            lines_clean = [line.strip() for line in lines]
            return queue_name in lines_clean
        return False

    if _check_queue_exists():
        return True

    logger.warning("Config queue does not exist, waiting...")
    start = time.time()
    while time.time() - start <= 2.0:
        if _check_queue_exists():
            return True
    return False


def _publish_config(
    logger: Logger,
    destination_site: str,
    config: PiggybackHubConfig,
    omd_root: Path,
    omd_site: str,
    customer: str,
) -> None:
    vhost = DEFAULT_VHOST_NAME if customer == DEFAULT_CUSTOMER else customer
    with Connection(APP_NAME, omd_root, omd_site, None, vhost=vhost) as conn:
        channel = conn.channel(PiggybackHubConfig)
        if vhost == DEFAULT_VHOST_NAME and not _wait_config_queue_ready(logger, channel):
            logger.error("Cannot publish piggyback hub config: Config queue does not exist")
            return
        channel.publish_for_site(destination_site, config, routing=CONFIG_ROUTE)
