#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime
from pathlib import Path
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest_mock import MockerFixture

from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.paths import default_config_dir

from cmk.gui.watolib import automatic_host_removal
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import FolderRulesets, Rule, RuleConditions, RuleOptions, Ruleset


@pytest.fixture(scope="function", autouse=True)
def fixture_sitenames(mocker: MockerFixture) -> None:
    mocker.patch.object(automatic_host_removal, "wato_site_ids", lambda: ["local"])


@pytest.fixture(name="activate_changes_mock")
def fixture_activate_changes(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(
        automatic_host_removal,
        "_activate_changes",
        mocker.MagicMock(),
    )


def test_remove_hosts_no_rules_early_return(
    activate_changes_mock: MagicMock,
    request_context: None,
) -> None:
    automatic_host_removal.execute_host_removal_job()
    activate_changes_mock.assert_not_called()


@pytest.fixture(name="setup_hosts")
def fixture_setup_hosts() -> None:
    folder_tree().root_folder().create_hosts(
        [
            (hostname, {}, None)
            for hostname in (
                HostName("host_crit_remove"),
                HostName("host_crit_keep"),
                HostName("host_ok"),
                HostName("host_removal_disabled"),
                HostName("host_no_rule_match"),
            )
        ],
    )


@pytest.fixture(name="setup_rules")
def fixture_setup_rules() -> None:
    root_folder = folder_tree().root_folder()
    ruleset = Ruleset("automatic_host_removal", {})
    ruleset.append_rule(
        root_folder,
        Rule(
            id_="1",
            folder=root_folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=root_folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["host_crit_remove", "host_crit_keep", "host_ok"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=(
                "enabled",
                {"checkmk_service_crit": 300},
            ),
        ),
    )
    ruleset.append_rule(
        root_folder,
        Rule(
            id_="1",
            folder=root_folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=root_folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["host_removal_disabled"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=(
                "disabled",
                None,
            ),
        ),
    )
    (Path(default_config_dir) / "main.mk").touch()
    FolderRulesets({"automatic_host_removal": ruleset}, folder=root_folder).save_folder()


@pytest.fixture(name="setup_livestatus_mock")
def fixture_setup_livestatus_mock(mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.set_sites(["local"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": "host_crit_remove",
                "description": "Check_MK",
                "last_state_change": 100,
                "state": 2,
            },
            {
                "host_name": "host_crit_keep",
                "description": "Check_MK",
                "last_state_change": 900,
                "state": 2,
            },
            {
                "host_name": "host_ok",
                "description": "Check_MK",
                "last_state_change": 456,
                "state": 0,
            },
            {
                "host_name": "host_removal_disabled",
                "description": "Check_MK",
                "last_state_change": 100,
                "state": 2,
            },
            {
                "host_name": "host_no_rule_match",
                "description": "Check_MK",
                "last_state_change": 100,
                "state": 2,
            },
        ],
    )


@pytest.fixture(name="mock_delete_hosts_automation")
def fixture_mock_delete_hosts_automation(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(
        automatic_host_removal,
        "delete_hosts",
        mocker.MagicMock(),
    )


@pytest.mark.usefixtures("setup_hosts")
@pytest.mark.usefixtures("setup_rules")
@pytest.mark.usefixtures("setup_livestatus_mock")
@pytest.mark.usefixtures("with_admin_login")
def test_execute_host_removal_job(
    mock_livestatus: MockLiveStatusConnection,
    activate_changes_mock: MagicMock,
    mock_delete_hosts_automation: MagicMock,
) -> None:
    with (
        time_machine.travel(datetime.datetime.fromtimestamp(1000, tz=ZoneInfo("UTC"))),
        mock_livestatus(expect_status_query=False),
    ):
        mock_livestatus.expect_query(
            [
                "GET services",
                "Columns: host_name last_state_change",
                "Filter: description = Check_MK",
                "Filter: state = 2",
                "ColumnHeaders: off",
            ]
        )
        automatic_host_removal.execute_host_removal_job()

    assert sorted(folder_tree().root_folder().all_hosts_recursively()) == [
        "host_crit_keep",
        "host_no_rule_match",
        "host_ok",
        "host_removal_disabled",
    ]
    mock_delete_hosts_automation.assert_called_once()
    activate_changes_mock.assert_called_once()
