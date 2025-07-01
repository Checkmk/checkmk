#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Show list of all views with buttons for editing"""

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.data_source import data_source_registry
from cmk.gui.i18n import _

from .store import get_all_views


def page_edit_views(config: Config) -> None:
    cols = [(_("Datasource"), lambda v: data_source_registry[v["datasource"]]().title)]
    visuals.page_list("views", _("Edit Views"), get_all_views(), cols)
