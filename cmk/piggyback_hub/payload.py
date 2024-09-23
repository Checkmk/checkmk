#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, CMKConnectionError, Connection
from cmk.piggyback import (
    get_piggyback_raw_data,
    load_last_distribution_time,
    PiggybackMessage,
    PiggybackMetaData,
    store_last_distribution_time,
    store_piggyback_raw_data,
)
from cmk.piggyback_hub.config import load_config, PiggybackHubConfig, Target
from cmk.piggyback_hub.paths import create_paths
from cmk.piggyback_hub.utils import SignalException

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
) -> Callable[[Channel[PiggybackPayload], PiggybackPayload], None]:
    def _on_message(_channel: Channel[PiggybackPayload], received: PiggybackPayload) -> None:
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

    return _on_message


def _filter_piggyback_hub_targets(
    config: PiggybackHubConfig, current_site_id: str
) -> Sequence[Target]:
    return [t for t in config.targets if t.site_id != current_site_id]


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
        for data in get_piggyback_raw_data(target_host, omd_root)
        if not _is_message_already_distributed(data.meta, omd_root)
    ]


def _send_message(
    channel: Channel,
    piggyback_message: PiggybackMessage,
    target_site_id: str,
    omd_root: Path,
    routing: str,
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
        routing=routing,
    )
    store_last_distribution_time(
        piggyback_message.meta.source,
        piggyback_message.meta.piggybacked,
        piggyback_message.meta.last_update,
        omd_root,
    )


class SendingPayloadThread(threading.Thread):
    def __init__(self, logger: logging.Logger, omd_root: Path):
        super().__init__()
        self.logger = logger
        self.omd_root = omd_root
        self.config_path = create_paths(omd_root).config

    def run(self):
        try:
            with Connection("piggyback-hub", self.omd_root) as conn:
                channel = conn.channel(PiggybackPayload)

                while True:
                    for target in _filter_piggyback_hub_targets(
                        load_config(self.config_path), self.omd_root.name
                    ):
                        for piggyback_message in _get_piggyback_raw_data_to_send(
                            target.host_name, self.omd_root
                        ):
                            self.logger.debug(
                                "Sending payload for piggybacked host '%s' from source host '%s' to site '%s'",
                                piggyback_message.meta.piggybacked,
                                piggyback_message.meta.source,
                                target.site_id,
                            )
                            _send_message(
                                channel, piggyback_message, target.site_id, self.omd_root, "payload"
                            )

                    time.sleep(SENDING_PAUSE)
        except CMKConnectionError:
            self.logger.error("RabbitMQ is not running. Stopping thread.")
        except SignalException:
            self.logger.debug("Stopping distributing messages")
            return
        except Exception as e:
            self.logger.exception("Unhandled exception: %s.", e)
