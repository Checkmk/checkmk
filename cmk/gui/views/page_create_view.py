#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provide dialog for creating a new view

This page makes the user select the single info and data source.
Then the user is redirected to the view editor dialog.
"""

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request


def page_create_view(config: Config) -> None:
    ds_class, ds_name = request.get_item_input("datasource", data_source_registry)
    visuals.page_create_visual(
        "views",
        ds_class().infos,
        next_url="edit_view.py?mode=create&datasource=%s&single_infos=%%s" % ds_name,
    )
