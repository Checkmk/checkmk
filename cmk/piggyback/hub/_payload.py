#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import signal
from collections.abc import Callable, Mapping, Sequence
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Self

from pydantic import BaseModel

from cmk.ccc.hostaddress import HostName

from cmk.messaging import Channel, CMKConnectionError, DeliveryTag, RoutingKey
from cmk.piggyback.backend import (
    get_messages_for,
    PiggybackMessage,
    store_piggyback_raw_data,
    watch_new_messages,
)

from ._config import AnnotatedHostName, load_config, PiggybackHubConfig
from ._utils import make_connection, make_log_and_exit


class PiggybackPayload(BaseModel):
    source_host: AnnotatedHostName
    raw_data: Mapping[AnnotatedHostName, Sequence[bytes]]
    message_timestamp: int
    contact_timestamp: int | None

    @classmethod
    def from_message(cls, message: PiggybackMessage) -> Self:
        return cls(
            source_host=message.meta.source,
            raw_data={message.meta.piggybacked: (message.raw_data,)},
            message_timestamp=message.meta.last_update,
            contact_timestamp=message.meta.last_contact,
        )


def save_payload_on_message(
    logger: logging.Logger,
    omd_root: Path,
) -> Callable[[Channel[PiggybackPayload], DeliveryTag, PiggybackPayload], None]:
    def _on_message(
        channel: Channel[PiggybackPayload], delivery_tag: DeliveryTag, received: PiggybackPayload
    ) -> None:
        logger.debug(
            "Received payload for piggybacked host from source host '%s'", received.source_host
        )
        store_piggyback_raw_data(
            source_hostname=received.source_host,
            piggybacked_raw_data=received.raw_data,
            message_timestamp=received.message_timestamp,
            contact_timestamp=received.contact_timestamp,
            omd_root=omd_root,
        )
        channel.acknowledge(delivery_tag)

    return _on_message


class SendingPayloadProcess(multiprocessing.Process):
    def __init__(
        self,
        logger: logging.Logger,
        omd_root: Path,
        reload_config: Event,
        crash_report_callback: Callable[[], str],
    ) -> None:
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.site = omd_root.name
        self.reload_config = reload_config
        self.crash_report_callback = crash_report_callback
        self.task_name = "publishing on queue 'payload'"

    def run(self):
        self.logger.info("Starting: %s", self.task_name)
        signal.signal(
            signal.SIGTERM,
            make_log_and_exit(self.logger.info, f"Terminating: {self.task_name}"),
        )

        config = load_config(self.omd_root)
        self.logger.debug("Loaded configuration: %r", config)

        failed_message = None
        try:
            while True:
                with make_connection(self.omd_root, self.site, self.logger, self.task_name) as conn:
                    try:
                        channel = conn.channel(PiggybackPayload)
                        if failed_message is not None:
                            # Retry in case the first time the channel was not available after make_connection
                            self._handle_message(channel, config, failed_message)
                            failed_message = None
                        for piggyback_message in watch_new_messages(self.omd_root):
                            config = self._check_for_config_reload(config)
                            self._handle_message(channel, config, piggyback_message)
                    except CMKConnectionError as exc:
                        failed_message = piggyback_message
                        self.logger.info("Reconnecting: %s: %s", self.task_name, exc)
        except CMKConnectionError as exc:
            self.logger.error("Connection error: %s: %s", self.task_name, exc)
        except Exception as exc:
            self.logger.exception("Exception: %s: %s", self.task_name, exc)
            crash_report_msg = self.crash_report_callback()
            self.logger.error(crash_report_msg)
            raise

    def _handle_message(
        self,
        channel: Channel[PiggybackPayload],
        config: PiggybackHubConfig,
        message: PiggybackMessage,
    ) -> None:
        if (site_id := config.locations.get(message.meta.piggybacked, self.site)) == self.site:
            return

        self.logger.debug(
            "%s: from host '%s' to host '%s' on site '%s'",
            self.task_name.title(),
            message.meta.source,
            message.meta.piggybacked,
            site_id,
        )
        channel.publish_for_site(
            site_id, PiggybackPayload.from_message(message), routing=RoutingKey("payload")
        )

    def _check_for_config_reload(self, current_config: PiggybackHubConfig) -> PiggybackHubConfig:
        if not self.reload_config.is_set():
            return current_config
        self.logger.info("Reloading configuration")
        config = load_config(self.omd_root)
        self.reload_config.clear()
        return config


def send_messages_oneshot(
    logger: logging.Logger,
    omd_root: Path,
    omd_site: str,
    targets: Mapping[HostName, str],
) -> None:
    task_name = "sending oneshot messages"
    logger.info("Starting: %s", task_name)

    hub_payloads = [
        (site_id, PiggybackPayload.from_message(message))
        for host, site_id in targets.items()
        for message in get_messages_for(host, omd_root)
    ]

    try:
        with make_connection(omd_root, omd_site, logger, task_name) as conn:
            channel = conn.channel(PiggybackPayload)
            for site, payload in hub_payloads:
                logger.debug(
                    "%s: to site '%s' for host '%s'",
                    task_name.title(),
                    site,
                    ",".join(payload.raw_data),  # it's only one.
                )
                channel.publish_for_site(site, payload, routing=RoutingKey("payload"))

    except CMKConnectionError as exc:
        logger.error("Connection error: %s: %s", task_name, exc)
