#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import config
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_mk_configuration import ConfigVariableGroupUserInterface
from cmk.gui.plugins.wato.utils import config_variable_registry, ConfigDomainGUI, ConfigVariable
from cmk.gui.valuespec import Age, Dictionary, ListOf, TextInput


@config_variable_registry.register
class ConfigVariableGraphTimeranges(ConfigVariable):
    def group(self):
        return ConfigVariableGroupUserInterface

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "graph_timeranges"

    def valuespec(self):
        return ListOf(
            Dictionary(
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
            default_value=config.graph_timeranges,
        )
