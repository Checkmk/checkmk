#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_mk_configuration import _transform_automatic_rediscover_parameters
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


def test_ui_theme_default_value(request_context) -> None:
    var = config_variable_registry["ui_theme"]()

    default_setting = var.domain()().default_globals()[var.ident()]
    assert default_setting == "modern-dark"

    assert var.valuespec().value_to_html(default_setting) == "Dark"


@pytest.mark.parametrize(
    "parameters, result",
    [
        ({}, {}),
        # These params have to be transformed
        (
            {
                "other_opt": "other opt",
                "service_whitelist": ["white"],
            },
            {
                "other_opt": "other opt",
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                    },
                ),
            },
        ),
        (
            {
                "other_opt": "other opt",
                "service_blacklist": ["black"],
            },
            {
                "other_opt": "other opt",
                "service_filters": (
                    "combined",
                    {
                        "service_blacklist": ["black"],
                    },
                ),
            },
        ),
        (
            {
                "other_opt": "other opt",
                "service_whitelist": ["white"],
                "service_blacklist": ["black"],
            },
            {
                "other_opt": "other opt",
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                        "service_blacklist": ["black"],
                    },
                ),
            },
        ),
        # These params go through the transform func
        (
            {
                "other_opt": "other opt",
                "service_filters": "service filters",
            },
            {
                "other_opt": "other opt",
                "service_filters": "service filters",
            },
        ),
    ],
)
def test__transform_automatic_rediscover_parameters(parameters, result) -> None:
    assert _transform_automatic_rediscover_parameters(parameters) == result
