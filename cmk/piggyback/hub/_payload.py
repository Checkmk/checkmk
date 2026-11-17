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
from typing import override, Self

from pydantic import BaseModel, RootModel

from cmk.ccc.hostaddress import HostName
from cmk.messaging import BindingKey, Channel, CMKConnectionError, DeliveryTag, RoutingKey
from cmk.piggyback.backend import (
    get_messages_for,
    PiggybackDataRemovedMessage,
    PiggybackMessage,
    remove_piggyback_raw_data,
    store_piggyback_raw_data,
    watch_new_messages,
)

from ._config import AnnotatedHostName, load_config, PiggybackHubConfig
from ._utils import make_connection, make_log_and_exit

PAYLOAD_ROUTE = RoutingKey("payload")
# Older sites have no binding for it, so they drop removals instead of failing to parse them.
# Removals share the payload queue, which keeps their order relative to the payload messages.
PAYLOAD_REMOVAL_ROUTE = RoutingKey("payload-removal")
PAYLOAD_BINDINGS = (BindingKey(PAYLOAD_ROUTE.value), BindingKey(PAYLOAD_REMOVAL_ROUTE.value))


class PiggybackPayloadRemoval(BaseModel):
    """The source has no data for the piggybacked host anymore"""

    source_host: AnnotatedHostName
    piggybacked_host: AnnotatedHostName


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


class PiggybackHubMessage(RootModel[PiggybackPayload | PiggybackPayloadRemoval]):
    """A message on the payload queue; the JSON is the one of the wrapped model"""


def save_payload_on_message(
    logger: logging.Logger,
    omd_root: Path,
) -> Callable[[Channel[PiggybackHubMessage], DeliveryTag, PiggybackHubMessage], None]:
    def _on_message(
        channel: Channel[PiggybackHubMessage],
        delivery_tag: DeliveryTag,
        received: PiggybackHubMessage,
    ) -> None:
        match received.root:
            case PiggybackPayload() as payload:
                logger.debug(
                    "Received payload for piggybacked host from source host '%(source_host)s'",
                    {"source_host": payload.source_host},
                )
                store_piggyback_raw_data(
                    source_hostname=payload.source_host,
                    piggybacked_raw_data=payload.raw_data,
                    message_timestamp=payload.message_timestamp,
                    contact_timestamp=payload.contact_timestamp,
                    omd_root=omd_root,
                )
            case PiggybackPayloadRemoval() as removal:
                logger.debug(
                    "Received removal of payload for host '%(piggybacked_host)s' "
                    "from source host '%(source_host)s'",
                    {
                        "piggybacked_host": removal.piggybacked_host,
                        "source_host": removal.source_host,
                    },
                )
                remove_piggyback_raw_data(removal.source_host, removal.piggybacked_host, omd_root)
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

    @override
    def run(self) -> None:
        self.logger.info("Starting: %(task_name)s", {"task_name": self.task_name})
        signal.signal(
            signal.SIGTERM,
            make_log_and_exit(self.logger.info, f"Terminating: {self.task_name}"),
        )

        config = load_config(self.omd_root)
        self.logger.debug("Loaded configuration: %(config)r", {"config": config})

        failed_message = None
        try:
            while True:
                with make_connection(self.omd_root, self.site, self.logger, self.task_name) as conn:
                    try:
                        # one channel for both routes keeps removals in order with the payloads
                        channel = conn.channel(PiggybackHubMessage)
                        if failed_message is not None:
                            # Retry in case the first time the channel was not available after make_connection
                            self._handle_message(channel, config, failed_message)
                            failed_message = None
                        for piggyback_message in watch_new_messages(self.omd_root):
                            config = self._check_for_config_reload(config)
                            self._handle_message(channel, config, piggyback_message)
                    except CMKConnectionError as exc:
                        failed_message = piggyback_message  # type: ignore[possibly-undefined]
                        self.logger.info(
                            "Reconnecting: %(task_name)s: %(exc)s",
                            {"task_name": self.task_name, "exc": exc},
                        )
        except CMKConnectionError:
            self.logger.exception("Connection error: %(task_name)s", {"task_name": self.task_name})
        except Exception as exc:
            self.logger.exception(
                "Exception: %(task_name)s: %(exc)s", {"task_name": self.task_name, "exc": exc}
            )
            crash_report_msg = self.crash_report_callback()
            # The traceback was already logged above; this only adds the crash report reference.
            self.logger.error(crash_report_msg)  # noqa: TRY400
            raise

    def _handle_message(
        self,
        channel: Channel[PiggybackHubMessage],
        config: PiggybackHubConfig,
        message: PiggybackMessage | PiggybackDataRemovedMessage,
    ) -> None:
        if isinstance(message, PiggybackDataRemovedMessage):
            source, piggybacked = message.source, message.piggybacked
            hub_message = PiggybackHubMessage(
                PiggybackPayloadRemoval(source_host=source, piggybacked_host=piggybacked)
            )
            routing = PAYLOAD_REMOVAL_ROUTE
        else:
            source, piggybacked = message.meta.source, message.meta.piggybacked
            hub_message = PiggybackHubMessage(PiggybackPayload.from_message(message))
            routing = PAYLOAD_ROUTE

        if (site_id := config.locations.get(piggybacked, self.site)) == self.site:
            return

        self.logger.debug(
            "%(task_name)s: %(routing)s from host '%(source)s' to host '%(piggybacked)s' "
            "on site '%(site)s'",
            {
                "task_name": self.task_name.title(),
                "routing": routing.value,
                "source": source,
                "piggybacked": piggybacked,
                "site": site_id,
            },
        )
        channel.publish_for_site(site_id, hub_message, routing=routing)

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
    logger.info("Starting: %(task_name)s", {"task_name": task_name})

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
                    "%(task_name)s: to site '%(site)s' for host '%(host)s'",
                    {
                        "task_name": task_name.title(),
                        "site": site,
                        "host": ",".join(payload.raw_data),  # it's only one.
                    },
                )
                channel.publish_for_site(site, payload, routing=PAYLOAD_ROUTE)

    except CMKConnectionError:
        logger.exception("Connection error: %(task_name)s", {"task_name": task_name})
