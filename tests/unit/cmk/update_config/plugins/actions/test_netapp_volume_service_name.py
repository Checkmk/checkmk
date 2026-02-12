#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Generator, Sequence
from contextlib import contextmanager

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import Item

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings

from cmk.update_config.plugins.actions.netapp_volume_service_name import (
    UpdateNetappVolumesServiceName,
)


@contextmanager
def _setup_autochecks(autochecks_setup: Sequence[tuple[CheckPluginName, Item]]) -> Generator[None]:
    host_name = "test_host"
    store = AutochecksStore(HostName(host_name))
    original_entries = store.read()
    try:
        entries = []
        for plugin_name, item in autochecks_setup:
            entry = AutocheckEntry(
                check_plugin_name=plugin_name, item=item, parameters={}, service_labels={}
            )
            entries.append(entry)
        store.write(entries)
        yield
    finally:
        store.write(original_entries)


@contextmanager
def _setup_global_settings(global_settings_setup: GlobalSettings) -> Generator[None]:
    original_global_settings = load_configuration_settings(full_config=True)
    try:
        save_global_settings(global_settings_setup)
        yield
    finally:
        save_global_settings(original_global_settings)


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["autochecks_setup", "initial_global_settings", "expected_global_settings"],
    [
        pytest.param(
            [],
            {"use_new_descriptions_for": []},
            {"use_new_descriptions_for": []},
            id="no_netapp_services_discovered",
        ),
        pytest.param(
            [(CheckPluginName("netapp_ontap_volumes"), "svm_name1:volume_name1")],
            {"use_new_descriptions_for": []},
            {"use_new_descriptions_for": ["netapp_ontap_snapshots", "netapp_ontap_volumes"]},
            id="only_new_services_enables_setting",
        ),
        pytest.param(
            [(CheckPluginName("netapp_api_volumes"), "svm_name1.volume_name1")],
            {"use_new_descriptions_for": []},
            {"use_new_descriptions_for": []},
            id="only_old_volumes_disables_setting",
        ),
        pytest.param(
            [
                (CheckPluginName("netapp_api_volumes"), "svm_name1.volume_name1"),
                (CheckPluginName("netapp_ontap_volumes"), "svm_name1:volume_name1"),
            ],
            {"use_new_descriptions_for": []},
            {"use_new_descriptions_for": ["netapp_ontap_snapshots", "netapp_ontap_volumes"]},
            id="both_old_and_new_services_enables_setting",
        ),
        pytest.param(
            [(CheckPluginName("netapp_api_volumes"), "svm_name1.volume_name1")],
            {"use_new_descriptions_for": {}},
            {"use_new_descriptions_for": {}},
            id="new_use_new_descriptions_for_format_does_nothing",
        ),
    ],
)
def test_update_action(
    autochecks_setup: Sequence[tuple[CheckPluginName, Item]],
    initial_global_settings: GlobalSettings,
    expected_global_settings: GlobalSettings,
) -> None:
    with _setup_global_settings(initial_global_settings), _setup_autochecks(autochecks_setup):
        action = UpdateNetappVolumesServiceName(
            name="netapp_volumes_service_name",
            title="NetApp Volumes Service Name",
            sort_index=40,
        )
        action(logging.getLogger())

        global_settings = load_configuration_settings(full_config=True)
        assert sorted(global_settings["use_new_descriptions_for"]) == sorted(
            expected_global_settings["use_new_descriptions_for"]
        )
