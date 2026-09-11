#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from cmk.gui.config import Config
from cmk.gui.global_settings.pages import app_data
from cmk.gui.i18n import _l
from cmk.gui.type_defs import IconNames
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Integer
from cmk.shared_typing import global_settings as shared


@pytest.fixture(name="factory_defaults")
def fixture_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give a factory default to the test variables only, which hides every real variable
    and with it every real group. The real lookup runs an automation that needs a site."""
    monkeypatch.setattr(
        ABCConfigDomain,
        "get_all_default_globals",
        classmethod(lambda cls: {"test_var_a": 1, "test_var_b": 2}),  # noqa: ARG005
    )


@contextmanager
def _registered(group: ConfigVariableGroup, *varnames: str) -> Iterator[None]:
    config_variable_group_registry.register(group)
    variables = [
        ConfigVariable(
            group=group,
            primary_domain=ConfigDomainGUI,
            ident=varname,
            form_spec=lambda context: Integer(title=Title("Test")),  # noqa: ARG005
        )
        for varname in varnames
    ]
    for variable in variables:
        config_variable_registry.register(variable)
    try:
        yield
    finally:
        for variable in variables:
            config_variable_registry.unregister(variable.ident())
        config_variable_group_registry.unregister(group.ident())


@pytest.mark.usefixtures("factory_defaults")
def test_a_registered_group_with_a_visible_variable_becomes_a_topic(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topics = app_data(load_config).topics
    assert [topic.headline for topic in topics] == ["Test group"]
    assert [variable.name for variable in topics[0].variables] == ["test_var_a"]


@pytest.mark.usefixtures("factory_defaults")
def test_a_group_without_visible_variables_yields_no_topic(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Empty group"), sort_index=1)):
        topics = app_data(load_config).topics
    assert topics == []


@pytest.mark.usefixtures("factory_defaults")
def test_the_group_icon_and_description_become_the_topic_header(load_config: Config) -> None:
    group = ConfigVariableGroup(
        title=_l("Test group"),
        sort_index=1,
        icon=IconNames.sites,
        description=_l("Configures the test"),
    )
    with _registered(group, "test_var_a"):
        topic = app_data(load_config).topics[0]
    assert topic.icon == shared.IconNames.sites
    assert topic.subline == "Configures the test"


@pytest.mark.usefixtures("factory_defaults")
def test_a_group_without_icon_and_description_gets_the_defaults(load_config: Config) -> None:
    with _registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topic = app_data(load_config).topics[0]
    assert topic.icon == shared.IconNames.configuration
    assert topic.subline == ""


@pytest.mark.usefixtures("factory_defaults")
def test_topics_follow_the_group_sort_index(load_config: Config) -> None:
    with (
        _registered(ConfigVariableGroup(title=_l("Later"), sort_index=20), "test_var_a"),
        _registered(ConfigVariableGroup(title=_l("Earlier"), sort_index=10), "test_var_b"),
    ):
        topics = app_data(load_config).topics
    assert [topic.headline for topic in topics] == ["Earlier", "Later"]
