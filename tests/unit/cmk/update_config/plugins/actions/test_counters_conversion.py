#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress

from cmk.checkengine.plugins import CheckPluginName, ServiceID
from cmk.checkengine.value_store import AllValueStoresStore, ValueStoreManager

from cmk.update_config.plugins.actions.counters_conversion import ConvertCounters


def test_new_files_are_ignored(tmp_path: Path) -> None:
    content = '[[["heute", "plugin", "item"], {"user-key": "42"}]]'

    (new_file := tmp_path / "heute").write_text(content)

    ConvertCounters.convert_counter_files(tmp_path, getLogger())

    assert new_file.read_text() == content


def test_beta_state_is_converted(tmp_path: Path) -> None:
    host = HostAddress("heute")
    service = ServiceID(CheckPluginName("plugin"), "item")
    old_content = '[[["heute", "plugin", "item", "user-key"], "42"]]'
    file = tmp_path / str(host)

    file.write_text(old_content)

    ConvertCounters.convert_counter_files(tmp_path, getLogger())

    assert file.exists()

    vsm = ValueStoreManager(host, AllValueStoresStore(file))
    with vsm.namespace(service):
        assert vsm.active_service_interface
        assert vsm.active_service_interface["user-key"] == 42


def test_old_files_are_converted(tmp_path: Path) -> None:
    host = HostAddress("heute")
    service = ServiceID(CheckPluginName("plugin"), "item")
    old_content = repr({(host, str(service[0]), service[1], "user-key"): 42})
    file = tmp_path / str(host)

    file.write_text(old_content)

    ConvertCounters.convert_counter_files(tmp_path, getLogger())

    assert file.exists()

    vsm = ValueStoreManager(host, AllValueStoresStore(file))
    with vsm.namespace(service):
        assert vsm.active_service_interface
        assert vsm.active_service_interface["user-key"] == 42
