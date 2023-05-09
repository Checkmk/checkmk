#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.check_mk_configuration import (
    _transform_automatic_rediscover_parameters,
    ConfigVariableGroupUserInterface,
)
from cmk.gui.plugins.wato.utils import config_variable_registry, ConfigDomainGUI
from cmk.gui.utils.theme import theme_choices
from cmk.gui.valuespec import DropdownChoice


def test_ui_theme_registration():
    var = config_variable_registry["ui_theme"]()
    assert var.domain() == ConfigDomainGUI
    assert var.group() == ConfigVariableGroupUserInterface

    valuespec = var.valuespec()
    assert isinstance(valuespec, DropdownChoice)
    assert valuespec.choices() == theme_choices()


def test_ui_theme_default_value(request_context):
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
def test__transform_automatic_rediscover_parameters(parameters, result):
    assert _transform_automatic_rediscover_parameters(parameters) == result
