#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user

from .dashlet import dashlet_registry, DashletConfig
from .store import get_permitted_dashboards, save_and_replicate_all_dashboards
from .type_defs import DashboardConfig

__all__ = ["ajax_dashlet_pos", "page_clone_dashlet", "page_delete_dashlet"]


def page_clone_dashlet(config: Config) -> None:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.var("name")
    if not board:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        dashlet_spec = dashboard["dashlets"][ident]
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    new_dashlet_spec = dashlet_spec.copy()
    dashlet_type = dashlet_registry[new_dashlet_spec["type"]]
    new_dashlet_spec["position"] = dashlet_type.initial_position()

    dashboard["dashlets"].append(new_dashlet_spec)
    dashboard["mtime"] = int(time.time())
    save_and_replicate_all_dashboards()

    raise HTTPRedirect(request.get_url_input("back"))


def page_delete_dashlet(config: Config) -> None:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.var("name")
    if not board:
        raise MKUserError("name", _("The name of the dashboard is missing."))

    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        _dashlet_spec = dashboard["dashlets"][ident]
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    dashboard["dashlets"].pop(ident)
    dashboard["mtime"] = int(time.time())
    save_and_replicate_all_dashboards()

    raise HTTPRedirect(request.get_url_input("back"))


def ajax_dashlet_pos(config: Config) -> None:
    dashlet_spec, board = check_ajax_update()

    board["mtime"] = int(time.time())

    dashlet_spec["position"] = (
        request.get_integer_input_mandatory("x"),
        request.get_integer_input_mandatory("y"),
    )
    dashlet_spec["size"] = (
        request.get_integer_input_mandatory("w"),
        request.get_integer_input_mandatory("h"),
    )
    save_and_replicate_all_dashboards()
    response.set_data("OK %d" % board["mtime"])


def check_ajax_update() -> tuple[DashletConfig, DashboardConfig]:
    if not user.may("general.edit_dashboards"):
        raise MKAuthException(_("You are not allowed to edit dashboards."))

    board = request.get_str_input_mandatory("name")
    ident = request.get_integer_input_mandatory("id")

    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        dashlet_spec = dashboard["dashlets"][ident]
    except IndexError:
        raise MKUserError("id", _("The element does not exist."))

    return dashlet_spec, dashboard
