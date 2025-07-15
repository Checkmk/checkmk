#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from itertools import chain

from cmk.ccc.site import SiteId
from cmk.gui.i18n import _, _u
from cmk.gui.sites import get_alias_of_host
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.utils.macros import MacroMapping, replace_macros_in_str


def macro_mapping_from_context(
    context: VisualContext,
    single_infos: SingleInfos,
    title: str,
    default_title: str,
    **additional_macros: str,
) -> MacroMapping:
    macro_mapping = {"$DEFAULT_TITLE$": default_title}
    macro_mapping.update(
        {
            macro: context[key][key]
            for macro, key in (
                ("$HOST_NAME$", "host"),
                ("$SERVICE_DESCRIPTION$", "service"),
            )
            if key in context and key in context[key] and key in single_infos
        }
    )

    if "$HOST_ALIAS$" in title and "$HOST_NAME$" in macro_mapping:
        macro_mapping["$HOST_ALIAS$"] = get_alias_of_host(
            SiteId(additional_macros.get("$SITE$", "")),
            macro_mapping["$HOST_NAME$"],
        )

    macro_mapping.update(additional_macros)

    return macro_mapping


def render_title_with_macros_string(
    context: VisualContext,
    single_infos: SingleInfos,
    title: str,
    default_title: str,
    **additional_macros: str,
) -> str:
    return replace_macros_in_str(
        _u(title),
        macro_mapping_from_context(
            context,
            single_infos,
            title,
            default_title,
            **additional_macros,
        ),
    )


def title_help_text_for_macros(
    single_infos: SingleInfos, additional_title_macros: Iterable[str]
) -> str:
    available_macros = chain(
        ["$DEFAULT_TITLE$ " + _u("(default title of the element)")],
        _get_title_macros_from_single_infos(single_infos),
        additional_title_macros,
    )
    macros_as_list = (
        f"<ul>{''.join(f'<li><tt>{macro}</tt></li>' for macro in available_macros)}</ul>"
    )
    return _("You can use the following macros to fill in the corresponding information:%s%s") % (
        macros_as_list,
        _(
            'These macros can be combined with arbitrary text elements, e.g. "some text '
            '<tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".'
        ),
    )


def _get_title_macros_from_single_infos(single_infos: SingleInfos) -> Iterable[str]:
    single_info_to_macros = {
        "host": ("$HOST_NAME$", "$HOST_ALIAS$"),
        "service": ("$SERVICE_DESCRIPTION$",),
    }
    for single_info in sorted(single_infos):
        yield from single_info_to_macros.get(single_info, [])
