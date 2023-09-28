#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Compute the title of a visual"""

from collections.abc import Sequence

from cmk.gui.config import active_config
from cmk.gui.i18n import _u
from cmk.gui.type_defs import FilterHTTPVariables, FilterName, ViewSpec, Visual, VisualContext

from ._filter_context import get_filter, get_singlecontext_vars, get_ubiquitary_filters


def visual_title(
    what: str,
    visual: Visual,
    context: VisualContext,
    skip_title_context: bool = False,
) -> str:
    title = _u(str(visual["title"]))

    # In case we have a site context given replace the $SITE$ macro in the titles.
    site_filter_vars = context.get("site", {})
    assert isinstance(site_filter_vars, dict)
    title = title.replace("$SITE$", site_filter_vars.get("site", ""))

    if visual["add_context_to_title"] and not skip_title_context:
        title = _add_context_title(context, visual["single_infos"], title)

    return title


def view_title(view_spec: ViewSpec, context: VisualContext) -> str:
    return visual_title("view", view_spec, context)


def _add_context_title(context: VisualContext, single_infos: Sequence[str], title: str) -> str:
    def filter_heading(
        filter_name: FilterName,
        filter_vars: FilterHTTPVariables,
    ) -> str | None:
        try:
            filt = get_filter(filter_name)
        except KeyError:
            return ""  # silently ignore not existing filters

        return filt.heading_info(filter_vars)

    extra_titles = [v for v in get_singlecontext_vars(context, single_infos).values() if v]

    # FIXME: Is this really only needed for visuals without single infos?
    if not single_infos:
        for filter_name, filt_vars in context.items():
            if heading := filter_heading(filter_name, filt_vars):
                extra_titles.append(heading)

    if extra_titles:
        title += " " + ", ".join(extra_titles)

    for fn in get_ubiquitary_filters():
        # Disable 'wato_folder' filter, if Setup is disabled or there is a single host view
        if fn == "wato_folder" and (not active_config.wato_enabled or "host" in single_infos):
            continue

        if heading := filter_heading(fn, context.get(fn, {})):
            title = heading + " - " + title

    return title
