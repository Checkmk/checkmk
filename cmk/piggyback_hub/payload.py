#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import multiprocessing
import signal
from collections.abc import Sequence
from pathlib import Path
from threading import Event
from typing import Callable

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, CMKConnectionError, Connection, DeliveryTag, RoutingKey
from cmk.piggyback import (
    PiggybackMessage,
    store_piggyback_raw_data,
    watch_new_messages,
)

from .config import load_config
from .paths import create_paths
from .utils import APP_NAME, make_log_and_exit


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


def _send_payload_message(
    channel: Channel,
    piggyback_message: PiggybackMessage,
    target_site_id: str,
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

        this_site = self.omd_root.name

        try:
            with Connection(APP_NAME, self.omd_root) as conn:
                channel = conn.channel(PiggybackPayload)

                for piggyback_message in watch_new_messages(self.omd_root):
                    if self.reload_config.is_set():
                        self.logger.debug("Reloading configuration")
                        config = load_config(self.paths)
                        self.reload_config.clear()

                    if (
                        site_id := config.targets.get(piggyback_message.meta.piggybacked, this_site)
                    ) is this_site:
                        continue

                    self.logger.debug(
                        "%s: from host '%s' to host '%s' on site '%s'",
                        self.task_name.title(),
                        piggyback_message.meta.source,
                        piggyback_message.meta.piggybacked,
                        site_id,
                    )
                    _send_payload_message(channel, piggyback_message, site_id)

        except CMKConnectionError as exc:
            self.logger.error("Stopping: %s: %s", self.task_name, exc)
        except Exception as exc:
            self.logger.exception("Exception: %s: %s", self.task_name, exc)
            raise
