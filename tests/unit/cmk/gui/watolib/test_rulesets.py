#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.paths import default_config_dir

from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.rulesets import FolderRulesets, Rule, RuleConditions, RuleOptions, Ruleset


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_analyse_host_ruleset() -> None:
    ruleset = _test_host_ruleset(folder := FolderTree().root_folder())
    _test_hosts(folder)
    (Path(default_config_dir) / "main.mk").touch()
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder()

    result = ruleset.analyse_ruleset(HostName("ding"), None, None, {})
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is False

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 1  # index of rule in folder
    assert isinstance(entry[2], Rule)

    result = ruleset.analyse_ruleset(HostName("dong"), None, None, {})
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is True

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 0  # index of rule in folder
    assert isinstance(entry[2], Rule)


def _test_hosts(folder: Folder) -> None:
    folder.create_hosts(
        [
            (HostName("ding"), {}, None),
            (HostName("dong"), {}, None),
        ]
    )


def _test_host_ruleset(folder: Folder) -> Ruleset:
    ruleset = Ruleset("only_hosts", {})
    ruleset.append_rule(
        folder,
        Rule(
            id_="1",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["dong"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=True,
        ),
    )
    ruleset.append_rule(
        folder,
        Rule(
            id_="2",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["ding"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=False,
        ),
    )
    return ruleset


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_analyse_service_ruleset() -> None:
    ruleset = _test_service_ruleset(folder := FolderTree().root_folder())
    _test_hosts(folder)
    (Path(default_config_dir) / "main.mk").touch()
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder()

    result = ruleset.analyse_ruleset(HostName("ding"), "Ding", None, {})
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is True

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 0  # index of rule in folder
    assert isinstance(entry[2], Rule)

    result = ruleset.analyse_ruleset(HostName("ding"), "Not matching", None, {})
    assert result == (None, [])


def _test_service_ruleset(folder: Folder) -> Ruleset:
    ruleset = Ruleset("ignored_services", {})
    ruleset.append_rule(
        folder,
        Rule(
            id_="1",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["ding"],
                service_description=["Ding"],
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=True,
        ),
    )
    return ruleset
