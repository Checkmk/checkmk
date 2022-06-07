#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Type

from cmk.gui.i18n import _
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
)
from cmk.gui.valuespec import HTTPUrl, TextInput, ValueSpec
from cmk.gui.watolib.config_domains import ConfigDomainGUI


@config_variable_group_registry.register
class ConfigVariableGroupSupport(ConfigVariableGroup):
    def title(self) -> str:
        return _("Support")

    def sort_index(self):
        return 80


@config_variable_registry.register
class ConfigVariableCrashReportURL(ConfigVariable):
    def group(self) -> Type[ConfigVariableGroup]:
        return ConfigVariableGroupSupport

    def domain(self) -> Type[ABCConfigDomain]:
        return ConfigDomainGUI

    def ident(self) -> str:
        return "crash_report_url"

    def valuespec(self) -> ValueSpec:
        return HTTPUrl(
            title=_("Crash report HTTP URL"),
            help=_("By default crash reports will be sent to our crash reporting server."),
            show_as_link=False,
        )


@config_variable_registry.register
class ConfigVariableCrashReportTarget(ConfigVariable):
    def group(self) -> Type[ConfigVariableGroup]:
        return ConfigVariableGroupSupport

    def domain(self) -> Type[ABCConfigDomain]:
        return ConfigDomainGUI

    def ident(self) -> str:
        return "crash_report_target"

    def valuespec(self) -> ValueSpec:
        return TextInput(
            title=_("Crash report fallback mail address"),
            help=_(
                "By default crash reports will be sent to our crash reporting server. In case "
                "this fails for some reason, the crash reports can be sent by mail to the "
                "address configured here."
            ),
            size=80,
        )
