#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from unittest.mock import Mock

import cmk.utils.paths
from cmk.utils.hostaddress import HostName

from cmk.messaging import DeliveryTag, RoutingKey
from cmk.piggyback import (
    get_messages_for,
    PiggybackMessage,
    PiggybackMetaData,
)
from cmk.piggyback_hub.payload import (
    _send_payload_message,
    PiggybackPayload,
    save_payload_on_message,
)


def test__on_message() -> None:
    test_logger = logging.getLogger("test")
    input_payload = PiggybackPayload(
        source_host="source",
        target_host="target",
        last_update=1640000020,
        last_contact=1640000000,
        sections=[b"line1", b"line2"],
    )
    on_message = save_payload_on_message(test_logger, cmk.utils.paths.omd_root)

    on_message(Mock(), DeliveryTag(0), input_payload)

    expected_payload = [
        PiggybackMessage(
            meta=PiggybackMetaData(
                source=HostName("source"),
                piggybacked=HostName("target"),
                last_update=1640000020,
                last_contact=1640000000,
            ),
            raw_data=b"line1\nline2\n",
        )
    ]
    actual_payload = get_messages_for(HostName("target"), cmk.utils.paths.omd_root)
    assert actual_payload == expected_payload


def test__send_message() -> None:
    channel = Mock()
    input_message = PiggybackMessage(
        meta=PiggybackMetaData(
            source=HostName("source_host"),
            piggybacked=HostName("target_host"),
            last_update=1234567890,
            last_contact=1234567891,
        ),
        raw_data=b"section1",
    )

    _send_payload_message(channel, input_message, "site_id")

    channel.publish_for_site.assert_called_once_with(
        "site_id",
        PiggybackPayload(
            source_host="source_host",
            target_host="target_host",
            last_update=1234567890,
            last_contact=1234567891,
            sections=[b"section1"],
        ),
        routing=RoutingKey("payload"),
    )
