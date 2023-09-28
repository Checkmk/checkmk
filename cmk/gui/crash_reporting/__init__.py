#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0.base import PainterRegistry
from cmk.gui.views.command import CommandRegistry
from cmk.gui.views.sorter import SorterRegistry

from .pages import PageCrash, PageDownloadCrashReport
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
) -> None:
    page_registry.register_page("crash")(PageCrash)
    page_registry.register_page("download_crash_report")(PageDownloadCrashReport)

    data_source_registry.register(DataSourceCrashReports)
    sorter_registry.register(SorterCrashTime)
    command_registry.register(CommandDeleteCrashReports)
    painter_registry.register(PainterCrashException)
    painter_registry.register(PainterCrashIdent)
    painter_registry.register(PainterCrashTime)
    painter_registry.register(PainterCrashType)
    painter_registry.register(PainterCrashSource)
    painter_registry.register(PainterCrashVersion)
