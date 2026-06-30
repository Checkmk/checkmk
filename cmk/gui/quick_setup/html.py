#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.table import Table
from cmk.gui.utils.html import HTML
from cmk.gui.watolib.configuration_bundle_store import (
    BundleId,
    is_locked_by_quick_setup,
    load_configuration_bundles,
)
from cmk.gui.watolib.mode import mode_url
from cmk.utils.global_ident_type import GlobalIdent

_BUNDLE_GROUP_EDIT_MODES: dict[str, str] = {}


def register_bundle_group_edit_mode(bundle_group: str, mode_name: str) -> None:
    _BUNDLE_GROUP_EDIT_MODES[bundle_group] = mode_name


def _quick_setup_link(ident: GlobalIdent) -> str:
    return quick_setup_link_url(ident)


def quick_setup_link_url(ident: GlobalIdent) -> str:
    """Returns the URL to the Quick Setup overview page for the given locked_by ident."""
    bundle_id = BundleId(ident["instance_id"])
    bundles = load_configuration_bundles()
    if bundle_id in bundles:
        bundle_group = bundles[bundle_id]["group"]
        if bundle_group in _BUNDLE_GROUP_EDIT_MODES:
            return mode_url(_BUNDLE_GROUP_EDIT_MODES[bundle_group], bundle_id=bundle_id)
    return mode_url("edit_configuration_bundle", bundle_id=bundle_id)


def quick_setup_render_link(ident: GlobalIdent) -> HTML:
    """Returns HTML for a link to the quick setup. This assumes the `ident` is for a quick setup."""
    return html.render_a(
        _("[%s] - Quick Setup") % ident["instance_id"],
        _quick_setup_link(ident),
        class_=["config-bundle-link"],
    )


def quick_setup_source_cell(table: Table, ident: GlobalIdent | None) -> None:
    """Adds the source cell to the table."""
    table.cell(_("Source"), css=["source"])
    if is_locked_by_quick_setup(ident, check_reference_exists=False):
        html.write_html(quick_setup_render_link(ident))
    else:
        html.write_text(None)


_BUNDLE_GROUP_PRODUCT_NAMES: dict[str, str] = {}


def register_bundle_group_product_name(bundle_group: str, product: str) -> None:
    """Register the user-facing product name (e.g. "OpenTelemetry") shown in the
    lock warning when a resource is locked by a bundle of this group."""
    _BUNDLE_GROUP_PRODUCT_NAMES[bundle_group] = product


def quick_setup_locked_warning(ident: GlobalIdent, type_name: str) -> None:
    """Creates a warning that the type is partially locked and managed by Quick setup.
    This assumes the `ident` is for a quick setup."""
    bundle_id = BundleId(ident["instance_id"])
    bundles = load_configuration_bundles()
    bundle = bundles.get(bundle_id)
    config_name = bundle["title"] if bundle is not None else ident["instance_id"]
    product = _BUNDLE_GROUP_PRODUCT_NAMES.get(bundle["group"]) if bundle is not None else None

    if product is not None:
        body = _(
            "This {type_name} is part of the {config_name} {product} configuration.<br>"
            "To access further parts of the {product} configuration, "
            "go to the related {product} configuration."
        ).format(
            type_name=type_name,
            config_name=config_name,
            product=product,
        )
    else:
        body = _(
            "This {type_name} is part of the {qs_name} configuration bundle.<br>"
            "It contains further parts that are accessible and summarized in an overview page."
        ).format(
            qs_name=ident["instance_id"],
            type_name=type_name,
        )

    html.div(
        html.render_div(
            html.render_h2(
                _("Part of Quick Setup: %s") % config_name,
                class_=["heading"],
            )
            + html.render_div(body)
            + html.render_div(
                html.render_a(
                    html.render_b(_("Go to %s overview") % config_name),
                    href=_quick_setup_link(ident),
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
                        "You are duplicating a %s that has been created by the Quick Setup and associated with the source"
                    )
                    % type_name
                    + html.render_a(
                        _("[%s] - Quick Setup") % ident["instance_id"],
                        _quick_setup_link(ident),
                        class_=["config-bundle-link"],
                        style="margin-left: 2px;",
                    )
                    + ".",
                    style="display: flex; align-items: center;",
                )
                + _(
                    "However, the duplicated %s will no longer be associated with the Quick Setup and this source."
                )
                % type_name
            ),
            class_=["content"],
        ),
        class_=["warning_container"],
    )
