#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from pathlib import Path
from threading import Event
from unittest.mock import Mock

from cmk.utils.hostaddress import HostName

from cmk.messaging import DeliveryTag
from cmk.piggyback_hub.config import PiggybackHubConfig, save_config_on_message, Target


def test_save_config_on_message(tmp_path: Path) -> None:
    test_logger = logging.getLogger("test")
    input_payload = PiggybackHubConfig(
        targets=[Target(host_name=HostName("test_host"), site_id="test_site")]
    )
    on_message = save_config_on_message(test_logger, tmp_path, (reload_config := Event()))

    config_dir = tmp_path / "etc/check_mk"
    config_dir.mkdir(parents=True)

    assert not reload_config.is_set()
    on_message(Mock(), DeliveryTag(0), input_payload)
    assert reload_config.is_set()

    expected_config = PiggybackHubConfig(
        targets=[Target(host_name=HostName("test_host"), site_id="test_site")]
    )
    with open(tmp_path / "etc/check_mk/piggyback_hub.conf") as f:
        actual_config = json.loads(f.read())
    assert PiggybackHubConfig.model_validate_json(actual_config) == expected_config
