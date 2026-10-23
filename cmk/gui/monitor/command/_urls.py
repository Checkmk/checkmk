#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The setup links the action dialogs offer next to their options.

The links the classic command forms render (see cmk.gui.views.command.commands),
but offered only where the page behind them would actually serve them - the
classic forms link some of them into a permission error instead.
"""

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.web.utils.urls import makeuri_contextless


def _may_reach(config: Config, permission: str) -> bool:
    """Whether the page would serve the request, rather than refuse it.

    Mirrors `ensure_static_permissions`: Setup as a whole has to be reachable,
    and the page's own permission is waived for those who may see all of it.
    """
    if not config.wato_enabled or not user.may("wato.use"):
        return False
    return user.may("wato.seeall") or user.may(f"wato.{permission}")


def acknowledge_presets_url(config: Config) -> str | None:
    """Where the acknowledge option defaults are edited."""
    if not _may_reach(config, "global"):
        return None
    return makeuri_contextless(
        request,
        [("varname", "acknowledge_problems")],
        filename="global_settings.py",
    )


def notification_rules_url(config: Config) -> str | None:
    """The rules that decide who a notification reaches."""
    if not _may_reach(config, "notifications"):
        return None
    return makeuri_contextless(request, [("mode", "notifications")], filename="wato.py")


def downtime_presets_url(config: Config) -> str | None:
    """Where the downtime duration presets are edited."""
    if not _may_reach(config, "global"):
        return None
    return makeuri_contextless(
        request,
        [("varname", "user_downtime_timeranges")],
        filename="global_settings.py",
    )
