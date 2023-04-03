#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.utils import ConfigVariableGroupUserInterface
from cmk.gui.plugins.watolib.utils import config_variable_registry
from cmk.gui.utils.theme import theme_choices
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.config_domains import ConfigDomainGUI


def test_ui_theme_registration() -> None:
    var = config_variable_registry["ui_theme"]()
    assert var.domain() == ConfigDomainGUI
    assert var.group() == ConfigVariableGroupUserInterface

    valuespec = var.valuespec()
    assert isinstance(valuespec, DropdownChoice)
    assert valuespec.choices() == theme_choices()


def test_ui_theme_default_value() -> None:
    var = config_variable_registry["ui_theme"]()

    default_setting = var.domain()().default_globals()[var.ident()]
    assert default_setting == "modern-dark"

    assert var.valuespec().value_to_html(default_setting) == "Dark"
