#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from unittest.mock import Mock

from cmk.utils.hostaddress import HostName

from cmk.piggyback_hub.config import (
    load_config,
    PiggybackHubConfig,
    save_config,
    save_config_on_message,
    Target,
)


def test_save_config_on_message(tmp_path: Path) -> None:
    test_logger = logging.getLogger("test")
    input_payload = PiggybackHubConfig(
        targets=[Target(host_name=HostName("test_host"), site_id="test_site")]
    )
    on_message = save_config_on_message(test_logger, tmp_path)

    config_dir = tmp_path / "etc/check_mk"
    config_dir.mkdir(parents=True)

    on_message(Mock(), input_payload)

    expected_config = PiggybackHubConfig(
        targets=[Target(host_name=HostName("test_host"), site_id="test_site")]
    )
    with open(tmp_path / "etc/check_mk/piggyback_hub.conf") as f:
        raw = f.read()
    assert PiggybackHubConfig.deserialize(raw) == expected_config


def test_save_and_load_config(tmp_path: Path) -> None:
    config_path = tmp_path / "foo"
    config = PiggybackHubConfig(
        targets=[
            Target(HostName("host-name-1"), "site-id-1"),
            Target(HostName("host-name-2"), "site-id-2"),
        ]
    )
    save_config(config_path, config)
    assert load_config(config_path) == config
