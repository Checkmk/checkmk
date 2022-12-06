#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import time

from cmk.utils.type_defs import UserId

from cmk.gui import visuals
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.plugins.dashboard.utils import (
    DashboardConfig,
    DashboardName,
    DashletConfig,
    get_all_dashboards,
    save_all_dashboards,
)


def load_dashboard_with_cloning(
    permitted_dashboards: dict[DashboardName, DashboardConfig],
    name: DashboardName,
    edit: bool = True,
) -> DashboardConfig:

    all_dashboards = get_all_dashboards()
    board = visuals.get_permissioned_visual(
        name,
        request.get_validated_type_input(UserId, "owner"),
        "dashboard",
        permitted_dashboards,
        all_dashboards,
    )
    if edit and board["owner"] == UserId.builtin():
        # Trying to edit a builtin dashboard results in doing a copy
        active_user = user.id
        assert active_user is not None
        board = copy.deepcopy(board)
        board["owner"] = active_user
        board["public"] = False

        all_dashboards[(active_user, name)] = board
        permitted_dashboards[name] = board
        save_all_dashboards()

    return board


def add_dashlet(dashlet_spec: DashletConfig, dashboard: DashboardConfig) -> None:
    dashboard["dashlets"].append(dashlet_spec)
    dashboard["mtime"] = int(time.time())
    save_all_dashboards()
