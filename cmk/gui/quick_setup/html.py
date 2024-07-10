#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.global_ident_type import GlobalIdent, is_locked_by_quick_setup

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.table import Table
from cmk.gui.utils.html import HTML


def quick_setup_render_link(ident: GlobalIdent) -> HTML:
    """Returns HTML for a link to the quick setup. This assumes the `ident` is for a quick setup."""
    return html.render_a(
        _("[%s] - Quick setup") % ident["instance_id"],  # TODO: QUICK-SETUP - host name
        "#",  # TODO: QUICK-SETUP - link to Quick setup
        class_=["config-bundle-link"],
    )


def quick_setup_source_cell(table: Table, ident: GlobalIdent | None) -> None:
    """Adds the source cell to the table."""
    table.cell(_("Source"), css=["source"])
    if is_locked_by_quick_setup(ident):
        html.write_html(quick_setup_render_link(ident))
    else:
        html.write_text(None)


def quick_setup_locked_warning(ident: GlobalIdent, type_name: str) -> None:
    """Creates a warning that the type is partially locked and managed by Quick setup.
    This assumes the `ident` is for a quick setup."""
    html.div(
        html.render_div(
            html.render_h2(  # TODO: QUICK-SETUP - rule type
                _("Configured with %s Quick setup") % ident["instance_id"],
                class_=["heading"],
            )
            + html.render_div(
                _(
                    "This {type_name} is part of the {host_name} configuration using Quick setup. "
                    "Some options cannot be edited to avoid conflicts.<br>Go to Quick "
                    "setup to edit all parameters of {host_name}."
                ).format(
                    host_name=ident["instance_id"],  # TODO: QUICK-SETUP - host name
                    type_name=type_name,
                ),
            )
            + html.render_div(
                html.render_a(
                    html.render_b(
                        _("Edit %s") % ident["instance_id"]  # TODO: QUICK-SETUP - host name
                    ),
                    href="#",  # TODO: QUICK-SETUP - link to Quick setup
                ),
                class_=["button-container"],
            ),
            class_=["content"],
        ),
        class_=["warning_container"],
    )


def quick_setup_duplication_warning(ident: GlobalIdent, type_name: str) -> None:
    """Creates a warning that the duplicated type will not be managed by Quick setup.
    This assumes the `ident` is for a quick setup."""
    html.div(
        html.render_div(
            html.render_h2(_("Source association changed"), class_=["heading"])
            + html.render_div(
                html.render_div(
                    _(
                        "You are duplicating a %s that has been created by the Quick setup and "
                        "associated with the source"
                    )
                    % type_name
                    + html.render_a(  # TODO: QUICK-SETUP - host name
                        _("[%s] - Quick setup") % ident["instance_id"],
                        "#",  # TODO: QUICK-SETUP - link to Quick setup
                        class_=["config-bundle-link"],
                        style="margin-left: 2px;",
                    )
                    + ".",
                    style="display: flex; align-items: center;",
                )
                + _(
                    "However, the duplicated %s will no longer be associated with the Quick setup "
                    "and this source."
                )
                % type_name
            ),
            class_=["content"],
        ),
        class_=["warning_container"],
    )
