#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from unittest.mock import Mock

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths

from cmk.messaging import DeliveryTag
from cmk.piggyback.backend import (
    get_messages_for,
    PiggybackMessage,
    PiggybackMetaData,
)
from cmk.piggyback.hub import _payload as payload


def test__on_message() -> None:
    test_logger = logging.getLogger("test")
    input_payload = payload.PiggybackPayload(
        source_host=HostName("source"),
        raw_data={HostName("target"): [b"line1\nline2"]},
        message_timestamp=1640000020,
        contact_timestamp=1640000000,
    )
    on_message = payload.save_payload_on_message(test_logger, cmk.utils.paths.omd_root)

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
