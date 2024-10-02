#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import signal
import time
from collections.abc import Sequence
from pathlib import Path
from threading import Event
from typing import Callable

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, CMKConnectionError, Connection, DeliveryTag, RoutingKey
from cmk.piggyback import (
    get_messages_for,
    load_last_distribution_time,
    PiggybackMessage,
    PiggybackMetaData,
    store_last_distribution_time,
    store_piggyback_raw_data,
)

from .config import load_config, PiggybackHubConfig
from .paths import create_paths
from .utils import APP_NAME, make_log_and_exit

SENDING_PAUSE = 60  # [s]


class PiggybackPayload(BaseModel):
    source_host: str
    target_host: str
    last_update: int
    last_contact: int | None
    sections: Sequence[bytes]


def save_payload_on_message(
    logger: logging.Logger,
    omd_root: Path,
) -> Callable[[Channel[PiggybackPayload], DeliveryTag, PiggybackPayload], None]:
    def _on_message(
        channel: Channel[PiggybackPayload], delivery_tag: DeliveryTag, received: PiggybackPayload
    ) -> None:
        logger.debug(
            "Received payload for piggybacked host '%s' from source host '%s'",
            received.target_host,
            received.source_host,
        )
        store_piggyback_raw_data(
            source_hostname=HostName(received.source_host),
            piggybacked_raw_data={HostName(received.target_host): received.sections},
            timestamp=received.last_update,
            omd_root=omd_root,
            status_file_timestamp=received.last_contact,
        )
        channel.acknowledge(delivery_tag)

    return _on_message


def _filter_piggyback_hub_targets(
    config: PiggybackHubConfig, current_site_id: str
) -> Sequence[tuple[HostName, str]]:
    return [
        (host_name, site_id)
        for host_name, site_id in config.targets.items()
        if site_id != current_site_id
    ]


def _is_message_already_distributed(meta: PiggybackMetaData, omd_root: Path) -> bool:
    if (
        distribution_time := load_last_distribution_time(meta.source, meta.piggybacked, omd_root)
    ) is None:
        return False

    return distribution_time >= meta.last_update


def _get_piggyback_raw_data_to_send(
    target_host: HostName, omd_root: Path
) -> Sequence[PiggybackMessage]:
    return [
        data
        for data in get_messages_for(target_host, omd_root)
        if not _is_message_already_distributed(data.meta, omd_root)
    ]


def _send_payload_message(
    channel: Channel,
    piggyback_message: PiggybackMessage,
    target_site_id: str,
    omd_root: Path,
) -> None:
    channel.publish_for_site(
        target_site_id,
        PiggybackPayload(
            source_host=piggyback_message.meta.source,
            target_host=piggyback_message.meta.piggybacked,
            last_update=piggyback_message.meta.last_update,
            last_contact=piggyback_message.meta.last_contact,
            sections=[piggyback_message.raw_data],
        ),
        routing=RoutingKey("payload"),
    )
    store_last_distribution_time(
        piggyback_message.meta.source,
        piggyback_message.meta.piggybacked,
        piggyback_message.meta.last_update,
        omd_root,
    )


class SendingPayloadProcess(multiprocessing.Process):
    def __init__(self, logger: logging.Logger, omd_root: Path, reload_config: Event) -> None:
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.paths = create_paths(omd_root)
        self.reload_config = reload_config
        self.task_name = "publishing on queue 'payload'"

    def run(self):
        self.logger.info("Starting: %s", self.task_name)
        signal.signal(
            signal.SIGTERM,
            make_log_and_exit(self.logger.debug, f"Stopping: {self.task_name}"),
        )

        config = load_config(self.paths)
        self.logger.debug("Loaded configuration: %r", config)

        try:
            with Connection(APP_NAME, self.omd_root) as conn:
                channel = conn.channel(PiggybackPayload)

                while True:
                    if self.reload_config.is_set():
                        self.logger.debug("Reloading configuration")
                        config = load_config(self.paths)
                        self.reload_config.clear()

                    for host_name, site_id in _filter_piggyback_hub_targets(
                        config, self.omd_root.name
                    ):
                        for piggyback_message in _get_piggyback_raw_data_to_send(
                            host_name, self.omd_root
                        ):
                            self.logger.debug(
                                "%s: from host '%s' to host '%s' on site '%s'",
                                self.task_name.title(),
                                piggyback_message.meta.source,
                                piggyback_message.meta.piggybacked,
                                site_id,
                            )
                            _send_payload_message(
                                channel, piggyback_message, site_id, self.omd_root
                            )

                    time.sleep(SENDING_PAUSE)
        except CMKConnectionError as exc:
            self.logger.error("Stopping: %s: %s", self.task_name, exc)
        except Exception as exc:
            self.logger.exception("Exception: %s: %s", self.task_name, exc)
            raise
