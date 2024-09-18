#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Realizes the steps before getting to the editor: Select the context type"""

from collections.abc import Sequence

from cmk.gui import forms
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_simple_form_page_menu
from cmk.gui.type_defs import SingleInfos, VisualTypeName
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import CascadingDropdown, DualListChoice, FixedValue, Transform, ValueSpec
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry

from ._breadcrumb import visual_page_breadcrumb


def page_create_visual(
    what: VisualTypeName, info_keys: SingleInfos, next_url: str | None = None
) -> None:
    visual_name = visual_type_registry[what]().title
    title = _("Create %s") % visual_name
    what_s = what[:-1]

    vs_infos = SingleInfoSelection(info_keys)

    breadcrumb = visual_page_breadcrumb(what, title, "create")
    make_header(
        html,
        title,
        breadcrumb,
        make_simple_form_page_menu(
            visual_name.capitalize(),
            breadcrumb,
            form_name="create_visual",
            button_name="_save",
            save_title=_("Continue"),
        ),
    )

    html.open_p()
    html.write_text_permissive(
        _(
            "Depending on the chosen datasource, a %s can list <i>multiple</i> or <i>single</i> objects. "
            "For example, the <i>services</i> datasource can be used to simply create a list "
            "of <i>multiple</i> services, a list of <i>multiple</i> services of a <i>single</i> host or even "
            "a list of services with the same name on <i>multiple</i> hosts. When you just want to "
            "create a list of objects, simply continue with the default choice (no restrictions). "
            "Alternatively, you have the option to restrict to a single host or to choose the type "
            "of objects you want to restrict to manually."
        )
        % what_s
    )
    html.close_p()

    if request.var("_save") and transactions.check_transaction():
        try:
            single_infos = vs_infos.from_html_vars("single_infos")
            vs_infos.validate_value(single_infos, "single_infos")
            next_url = (
                next_url or "edit_" + what_s + ".py?mode=create"
            ) + "&single_infos=%s" % ",".join(single_infos)
            raise HTTPRedirect(next_url)
        except MKUserError as e:
            html.user_error(e)

    with html.form_context("create_visual"):
        html.hidden_field("mode", "create")

        forms.header(_("Select specific object type"))
        forms.section(vs_infos.title())
        vs_infos.render_input("single_infos", "")
        html.help(vs_infos.help())
        forms.end()

        html.hidden_fields()
    html.footer()


def SingleInfoSelection(info_keys: SingleInfos) -> Transform:
    infos = [visual_info_registry[key]() for key in info_keys]
    manual_choices = [
        (i.ident, _("Show information of a single %s") % i.title)
        for i in sorted(infos, key=lambda inf: (inf.sort_index, inf.title))
    ]

    cascading_dropdown_choices: list[tuple[str, str, ValueSpec]] = [
        (
            "no_restriction",
            _("No restrictions to specific objects"),
            FixedValue(
                value=[],
                totext="",
            ),
        ),
    ]

    if any(manual_choice[0] == "host" for manual_choice in manual_choices):
        cascading_dropdown_choices.append(
            (
                "single_host",
                _("Restrict to a single host"),
                FixedValue(
                    value=["host"],
                    totext="",
                ),
            ),
        )

    cascading_dropdown_choices.append(
        (
            "manual_selection",
            _("Configure restrictions manually"),
            DualListChoice(
                title=_("Specific objects"),
                choices=manual_choices,
                rows=10,
                allow_empty=False,
            ),
        ),
    )

    # We need these transformations because the code which further processes the user input to this
    # valuespec expects a list of strings (since this was once the DualListChoice now located under
    # "manual_selection").
    return Transform(
        valuespec=CascadingDropdown(
            choices=cascading_dropdown_choices,
            title=_("Specific objects"),
            sorted=False,
        ),
        from_valuespec=_single_info_selection_from_valuespec,
        to_valuespec=_single_info_selection_to_valuespec,
    )


def _single_info_selection_to_valuespec(restrictions: Sequence[str]) -> tuple[str, Sequence[str]]:
    if not restrictions:
        choice_name = "no_restriction"
    elif restrictions == ["host"]:
        choice_name = "single_host"
    else:
        choice_name = "manual_selection"
    return choice_name, restrictions


def _single_info_selection_from_valuespec(
    name_and_restrictions: tuple[str, Sequence[str]],
) -> Sequence[str]:
    return name_and_restrictions[1]
