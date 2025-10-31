#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.views.command import CommandRegistry
from cmk.gui.views.sorter import SorterRegistry
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.watolib.config_domain_name import ConfigVariableGroupRegistry, ConfigVariableRegistry

from . import pages as crash_reporting_pages
from ._settings import ConfigVariableCrashReportTarget, ConfigVariableCrashReportURL
from .views import (
    CommandDeleteCrashReports,
    DataSourceCrashReports,
    FilterCrashCheckType,
    FilterCrashException,
    FilterCrashHost,
    FilterCrashId,
    FilterCrashItem,
    FilterCrashServiceName,
    FilterCrashSite,
    FilterCrashSource,
    FilterCrashTime,
    FilterCrashType,
    FilterCrashVersion,
    PainterCrashCheckType,
    PainterCrashException,
    PainterCrashHost,
    PainterCrashIdent,
    PainterCrashItem,
    PainterCrashServiceName,
    PainterCrashSource,
    PainterCrashTime,
    PainterCrashType,
    PainterCrashVersion,
    SorterCrashCheckType,
    SorterCrashException,
    SorterCrashHost,
    SorterCrashIdent,
    SorterCrashItem,
    SorterCrashServiceName,
    SorterCrashSource,
    SorterCrashTime,
    SorterCrashType,
    SorterCrashVersion,
)


def register(
    page_registry: PageRegistry,
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    command_registry: CommandRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    config_variable_registry: ConfigVariableRegistry,
    filter_registry: FilterRegistry,
) -> None:
    crash_reporting_pages.register(page_registry)
    data_source_registry.register(DataSourceCrashReports)
    sorter_registry.register(SorterCrashCheckType)
    sorter_registry.register(SorterCrashHost)
    sorter_registry.register(SorterCrashItem)
    sorter_registry.register(SorterCrashServiceName)
    sorter_registry.register(SorterCrashTime)
    sorter_registry.register(SorterCrashCheckType)
    sorter_registry.register(SorterCrashException)
    sorter_registry.register(SorterCrashIdent)
    sorter_registry.register(SorterCrashServiceName)
    sorter_registry.register(SorterCrashSource)
    sorter_registry.register(SorterCrashType)
    sorter_registry.register(SorterCrashVersion)
    command_registry.register(CommandDeleteCrashReports)
    painter_registry.register(PainterCrashCheckType)
    painter_registry.register(PainterCrashException)
    painter_registry.register(PainterCrashHost)
    painter_registry.register(PainterCrashIdent)
    painter_registry.register(PainterCrashItem)
    painter_registry.register(PainterCrashServiceName)
    painter_registry.register(PainterCrashSource)
    painter_registry.register(PainterCrashTime)
    painter_registry.register(PainterCrashType)
    painter_registry.register(PainterCrashVersion)
    config_variable_registry.register(ConfigVariableCrashReportTarget)
    config_variable_registry.register(ConfigVariableCrashReportURL)
    filter_registry.register(FilterCrashCheckType)
    filter_registry.register(FilterCrashException)
    filter_registry.register(FilterCrashHost)
    filter_registry.register(FilterCrashId)
    filter_registry.register(FilterCrashItem)
    filter_registry.register(FilterCrashServiceName)
    filter_registry.register(FilterCrashSite)
    filter_registry.register(FilterCrashSource)
    filter_registry.register(FilterCrashTime)
    filter_registry.register(FilterCrashType)
    filter_registry.register(FilterCrashVersion)
