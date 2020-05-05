#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import os

import cmk.gui.config as config

from testlib import cmk_path

from cmk.gui.valuespec import (
    DropdownChoice,)

from cmk.gui.plugins.wato.check_mk_configuration import (ConfigVariableGroupUserInterface,
                                                         agent_config_mk_agent_sections)

from cmk.gui.plugins.wato import (
    config_variable_registry,
    ConfigDomainGUI,
)


@pytest.fixture(autouse=True)
def initialize_default_config():
    config._initialize_with_default_config()


def test_ui_theme_registration():
    var = config_variable_registry["ui_theme"]()
    assert var.domain() == ConfigDomainGUI
    assert var.group() == ConfigVariableGroupUserInterface

    valuespec = var.valuespec()
    assert isinstance(valuespec, DropdownChoice)
    assert valuespec.choices() == config.theme_choices()


def test_ui_theme_default_value(register_builtin_html):
    var = config_variable_registry["ui_theme"]()

    default_setting = var.domain()().default_globals()[var.ident()]
    assert default_setting == "classic"

    assert var.valuespec().value_to_text(default_setting) == "Classic"


def test_exclude_section_options():
    actual = [skip_section for skip_section, section_title in agent_config_mk_agent_sections()]
    agent_skip_functions = os.popen(
        "grep \"\$MK_SKIP_[A-Z]*[_A-Z]*\" %s/agents/check_mk_agent.linux -o" % cmk_path()).read()
    expected = [
        skip_section.replace("$MK_SKIP_", "").lower()
        for skip_section in agent_skip_functions.split("\n")
        if "$MK_SKIP_" in skip_section
    ]
    for agent_section in expected:
        assert agent_section in actual
