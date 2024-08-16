#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from unittest.mock import Mock

import pytest

import cmk.utils.paths
from cmk.utils.hostaddress import HostName

from cmk.piggyback import (
    get_piggyback_raw_data,
    load_last_distribution_time,
    PiggybackMessage,
    PiggybackMetaData,
    store_last_distribution_time,
    store_piggyback_raw_data,
)
from cmk.piggyback_hub.main import (
    _create_on_message,
    _get_piggyback_raw_data_to_send,
    _load_piggyback_targets,
    _send_message,
    PiggybackPayload,
    Target,
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

    _send_message(channel, input_message, "site_id", cmk.utils.paths.omd_root)

    channel.publish_for_site.assert_called_once_with(
        "site_id",
        PiggybackPayload(
            source_host="source_host",
            target_host="target_host",
            last_update=1234567890,
            last_contact=1234567891,
            sections=[b"section1"],
        ),
    )
    actual_last_distribution_time = load_last_distribution_time(
        HostName("source_host"), HostName("target_host"), cmk.utils.paths.omd_root
    )
    assert actual_last_distribution_time == 1234567890


@pytest.mark.parametrize(
    "last_update, last_distribution_time, expected_result",
    [
        pytest.param(15000000, 15000000, [], id="already_distributed"),
        pytest.param(
            15000000,
            10000000,
            [
                PiggybackMessage(
                    meta=PiggybackMetaData(
                        source=HostName("source"),
                        piggybacked=HostName("target"),
                        last_update=15000000,
                        last_contact=15000000,
                    ),
                    raw_data=b"line1\nline2\n",
                )
            ],
            id="not_distributed",
        ),
    ],
)
def test__get_piggyback_raw_data_to_send(
    last_update: float, last_distribution_time: float, expected_result: Sequence[PiggybackMessage]
) -> None:
    piggybacked_host = HostName("target")
    store_piggyback_raw_data(
        HostName("source"),
        {piggybacked_host: (b"line1", b"line2")},
        last_update,
        cmk.utils.paths.omd_root,
    )
    store_last_distribution_time(
        HostName("source"), piggybacked_host, last_distribution_time, cmk.utils.paths.omd_root
    )

    actual_payload = _get_piggyback_raw_data_to_send(piggybacked_host, cmk.utils.paths.omd_root)
    assert actual_payload == expected_result


def test__load_piggyback_targets_missing_config_file(tmpdir: Path) -> None:
    actual_targets = _load_piggyback_targets(tmpdir / "piggyback_hub.conf", "site1")
    assert not actual_targets


@pytest.mark.parametrize(
    "config, expected_targets",
    [
        pytest.param([{"host_name": "host1", "site_id": "site1"}], [], id="skip_self"),
        pytest.param(
            [
                {"host_name": "host1", "site_id": "site1"},
                {"host_name": "host2", "site_id": "site2"},
            ],
            [Target(host_name=HostName("host2"), site_id="site2")],
            id="additional_site",
        ),
    ],
)
def test__load_piggyback_targets(
    tmpdir: Path, config: Sequence[Mapping[str, str]], expected_targets: Sequence[Target]
) -> None:
    config_file = tmpdir / "piggyback_hub.conf"
    with open(config_file, "w") as f:
        f.write(json.dumps(config))

    actual_targets = _load_piggyback_targets(tmpdir / "piggyback_hub.conf", "site1")
    assert actual_targets == expected_targets
