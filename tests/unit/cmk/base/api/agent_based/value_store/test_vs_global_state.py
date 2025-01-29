#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest import MonkeyPatch

from cmk.ccc import store

from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import CheckPluginName, ServiceID

from cmk.base.api.agent_based.value_store import ValueStoreManager

from cmk.agent_based.v1.value_store import get_value_store, set_value_store_manager


def test_load_host_value_store_loads_file(monkeypatch: MonkeyPatch) -> None:
    service_id = ServiceID(CheckPluginName("test_service"), None)
    raw_content = (
        '[[["test_load_host_value_store_loads_file", "test_service", null, "loaded_file"], "True"]]'
    )

    monkeypatch.setattr(
        store,
        "load_text_from_file",
        lambda *_a, **_kw: raw_content,
    )

    with set_value_store_manager(
        ValueStoreManager(HostName("test_load_host_value_store_loads_file")),
        store_changes=False,
    ) as mgr:
        with mgr.namespace(service_id):
            assert get_value_store()["loaded_file"] is True  # trueish is not enough
