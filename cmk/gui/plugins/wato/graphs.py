#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Type

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import ConfigVariableGroupUserInterface
from cmk.gui.plugins.watolib.utils import ABCConfigDomain, config_variable_registry, ConfigVariable
from cmk.gui.valuespec import Age, Dictionary, ListOf, TextInput
from cmk.gui.watolib.config_domains import ConfigDomainGUI


@config_variable_registry.register
class ConfigVariableGraphTimeranges(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self) -> Type[ABCConfigDomain]:
        return ConfigDomainGUI

    def ident(self) -> str:
        return "graph_timeranges"

    def valuespec(self):
        return ListOf(
            valuespec=Dictionary(
                optional_keys=[],
                elements=[
                    (
                        "title",
                        TextInput(
                            title=_("Title"),
                            allow_empty=False,
                        ),
                    ),
                    (
                        "duration",
                        Age(
                            title=_("Duration"),
                        ),
                    ),
                ],
            ),
            title=_("Custom graph timeranges"),
            movable=True,
            totext=_("%d timeranges"),
            default_value=active_config.graph_timeranges,
        )
