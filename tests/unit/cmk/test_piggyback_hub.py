#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import cmk.utils.paths
from cmk.utils.hostaddress import HostName

from cmk.piggyback import get_piggyback_raw_data, PiggybackMessage, PiggybackMetaData
from cmk.piggyback_hub.main import _create_on_message, PiggybackPayload


def test__on_message() -> None:
    test_logger = logging.getLogger("test")
    input_payload = PiggybackPayload(
        source_host="source",
        target_host="target",
        last_update=1640000020,
        last_contact=1640000000,
        sections=[b"line1", b"line2"],
    )
    on_message = _create_on_message(test_logger, cmk.utils.paths.omd_root)

    on_message(None, None, None, input_payload)

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
    actual_payload = get_piggyback_raw_data(HostName("target"), cmk.utils.paths.omd_root)
    assert actual_payload == expected_payload
