#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple
from unittest import mock

import pytest


class _MockVSManager(NamedTuple):
    active_service_interface: Mapping[str, object]


@pytest.fixture()
def initialised_item_state():
    mock_vs = _MockVSManager({})
    with mock.patch(
        "cmk.agent_based.v1.value_store._active_host_value_store",
        mock_vs,
    ):
        yield
