#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from pytest import MonkeyPatch

import cmk.utils.store as store
from cmk.utils.type_defs import HostName

from cmk.checkers.check_table import ServiceID
from cmk.checkers.checking import CheckPluginName

from cmk.base.api.agent_based.value_store._global_state import (
    get_value_store,
    load_host_value_store,
)

_TEST_KEY = ("check", "item", "user-key")


def test_load_host_value_store_loads_file(monkeypatch: MonkeyPatch) -> None:
    service_id = ServiceID(CheckPluginName("test_service"), None)

    monkeypatch.setattr(
        store,
        "load_text_from_file",
        lambda *_a, **_kw: "{('test_load_host_value_store_loads_file', '%s', %r, 'loaded_file'): True}"
        % service_id,
    )

    with load_host_value_store(
        HostName("test_load_host_value_store_loads_file"),
        store_changes=False,
    ) as mgr:
        with mgr.namespace(service_id):
            assert get_value_store()["loaded_file"]
