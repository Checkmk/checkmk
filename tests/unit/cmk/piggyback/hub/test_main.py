#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from multiprocessing import Event as make_event
from pathlib import Path
from unittest.mock import Mock

from cmk.ccc.hostaddress import HostName

from cmk.messaging import DeliveryTag
from cmk.piggyback.hub._config import (
    ConfigType,
    load_config,
    PiggybackHubConfig,
)
from cmk.piggyback.hub._main import handle_received_config


def test_handle_received_config(tmp_path: Path) -> None:
    test_logger = logging.getLogger("test")
    input_payload = PiggybackHubConfig(
        type=ConfigType.PERSISTED, locations={HostName("test_host"): "test_site"}
    )
    on_message = handle_received_config(
        test_logger, tmp_path, "mysite", (reload_config := make_event())
    )

    assert not reload_config.is_set()
    on_message(Mock(), DeliveryTag(0), input_payload)
    assert reload_config.is_set()

    assert load_config(tmp_path) == input_payload
