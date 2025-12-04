#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.oauth2_connections.watolib.store import (
    is_locked_by_oauth2_connection,
    load_oauth2_connections,
)
from cmk.gui.utils.html import HTML
from cmk.gui.watolib.mode import mode_url
from cmk.utils.global_ident_type import GlobalIdent


def oauth2_render_link(ident: GlobalIdent) -> HTML:
    instance_id = ident["instance_id"]
    title = load_oauth2_connections()[instance_id]["title"]
    return html.render_a(
        _("[%s] - OAuth2 connection") % title,
        mode_url("edit_oauth2_connection", ident=instance_id),
        class_=["config-bundle-link"],
    )


def oauth2_source_cell(ident: GlobalIdent | None) -> None:
    """Adds the source cell to the table."""
    if is_locked_by_oauth2_connection(ident, check_reference_exists=False):
        html.write_html(oauth2_render_link(ident))
    else:
        html.write_text(None)
