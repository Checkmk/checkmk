#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.views.command import CommandRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariableGroupRegistry, ConfigVariableRegistry

from . import pages as crash_reporting_pages
from ._settings import ConfigVariableCrashReportTarget, ConfigVariableCrashReportURL
from .views import (
    CommandDeleteCrashReports,
    DataSourceCrashReports,
    PainterCrashException,
    PainterCrashIdent,
    PainterCrashSource,
    PainterCrashTime,
    PainterCrashType,
    PainterCrashVersion,
    SorterCrashTime,
)


def register(
    page_registry: PageRegistry,
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    command_registry: CommandRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
) -> None:
    crash_reporting_pages.register(page_registry)
    data_source_registry.register(DataSourceCrashReports)
    sorter_registry.register(SorterCrashTime)
    command_registry.register(CommandDeleteCrashReports)
    painter_registry.register(PainterCrashException)
    painter_registry.register(PainterCrashIdent)
    painter_registry.register(PainterCrashTime)
    painter_registry.register(PainterCrashType)
    painter_registry.register(PainterCrashSource)
    painter_registry.register(PainterCrashVersion)
    config_variable_registry.register(ConfigVariableCrashReportTarget)
    config_variable_registry.register(ConfigVariableCrashReportURL)
