#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from contextlib import suppress
from typing import cast

from cmk.gui import visuals
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import Request, request, response
from cmk.gui.type_defs import (
    FilterName,
    HTTPVariables,
    InfoName,
    Row,
    SingleInfos,
    ViewSpec,
    Visual,
    VisualLinkSpec,
    VisualName,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry, VisualType


def render_link_to_view(
    content: str | HTML, row: Row, link_spec: VisualLinkSpec, *, request: Request
) -> str | HTML:
    if display_options.disabled(display_options.I):
        return content

    url = url_to_visual(row, link_spec, request=request)
    if url:
        return HTMLWriter.render_a(content, href=url)
    return content


def url_to_visual(row: Row, link_spec: VisualLinkSpec, *, request: Request) -> str | None:
    if display_options.disabled(display_options.I):
        return None

    visual = _get_visual_by_link_spec(link_spec)
    if not visual:
        return None

    visual_type = visual_type_registry[link_spec.type_name]()

    if visual_type.ident == "views":
        # TOOD: We need to change the logic to be able to type this correctly
        visual = cast(ViewSpec, visual)
        datasource = data_source_registry[visual["datasource"]]()
        infos = datasource.infos
        link_filters = datasource.link_filters
    elif visual_type.ident == "dashboards":
        # TODO: Is this "infos" correct?
        infos = []
        link_filters = {}
    else:
        raise NotImplementedError(f"Unsupported visual type: {visual_type}")

    singlecontext_request_vars = _get_singlecontext_html_vars_from_row(
        visual["name"], row, infos, visual["single_infos"], link_filters
    )

    return make_linked_visual_url(
        visual_type, visual, singlecontext_request_vars, is_mobile(request, response)
    )


def _get_visual_by_link_spec(link_spec: VisualLinkSpec | None) -> Visual | None:
    if link_spec is None:
        return None

    visual_type = visual_type_registry[link_spec.type_name]()
    visual_type.load_handler()
    available_visuals = visual_type.permitted_visuals

    with suppress(KeyError):
        return available_visuals[link_spec.name]  # type: ignore[no-any-return]

    return None


def _get_singlecontext_html_vars_from_row(
    visual_name: VisualName,
    row: Row,
    infos: SingleInfos,
    single_infos: SingleInfos,
    link_filters: dict[str, str],
) -> dict[str, str]:
    # Get the context type of the view to link to, then get the parameters of this context type
    # and try to construct the context from the data of the row
    url_vars: dict[str, str] = {}
    for info_key in single_infos:
        # Determine which filters (their names) need to be set for specifying in order to select
        # correct context for the target view.
        for filter_name in visuals.info_params(info_key):
            filter_object = visuals.get_filter(filter_name)
            # Get the list of URI vars to be set for that filter
            try:
                url_vars.update(filter_object.request_vars_from_row(row))
            except KeyError:
                # The information needed for a mandatory filter (single context) is not available.
                # Continue without failing: The target site will show up a warning and ask for the
                # missing information.
                pass

    # See get_link_filter_names() comment for details
    for src_key, dst_key in visuals.get_link_filter_names(single_infos, infos, link_filters):
        try:
            url_vars.update(visuals.get_filter(src_key).request_vars_from_row(row))
        except KeyError:
            pass

        try:
            url_vars.update(visuals.get_filter(dst_key).request_vars_from_row(row))
        except KeyError:
            pass

    add_site_hint = _may_add_site_hint(
        visual_name,
        info_keys=tuple(visual_info_registry.keys()),
        single_info_keys=tuple(single_infos),
        filter_names=tuple(url_vars.keys()),
    )
    if add_site_hint and row.get("site"):
        url_vars["site"] = row["site"]

    return url_vars


def make_linked_visual_url(
    visual_type: VisualType,
    visual: Visual,
    singlecontext_request_vars: dict[str, str],
    mobile: bool,
) -> str:
    """Compute URLs to link from a view to other dashboards and views"""
    name = visual["name"]

    filename = visual_type.show_url
    if mobile and visual_type.show_url == "view.py":
        filename = "mobile_" + visual_type.show_url

    # Include visual default context. This comes from the hard_filters. Linked
    # view would have no _active flag. Thus prepend the default context
    required_vars: HTTPVariables = [(visual_type.ident_attr, name)]
    required_vars += visuals.context_to_uri_vars(visual.get("context", {}))

    # add context link to this visual. For reports we put in
    # the *complete* context, even the non-single one.
    if visual_type.multicontext_links:
        # Keeping the _active flag is a long distance hack to be able to rebuild the
        # filters on the linked view using the visuals.VisualFilterListWithAddPopup.from_html_vars
        return makeuri(
            request, required_vars, filename=filename, delvars=["show_checkboxes", "selection"]
        )

    vars_values = get_linked_visual_request_vars(visual, singlecontext_request_vars)
    http_vars = vars_values + required_vars
    # For views and dashboards currently the current filter settings
    return makeuri_contextless(
        request,
        _replace_group_vars(http_vars) if visual_type.ident == "dashboards" else http_vars,
        filename=filename,
    )


def _replace_group_vars(vars_: HTTPVariables) -> HTTPVariables:
    """
    This is only needed for VisualTypeDashboards to get the correct http vars
    for host and service groups. Dashboards have no datasource so this is
    not covered by the current mechanism.

    Replace hostgroup and servicegroup variables with opthost_group /
    optservice_group
    """
    filtered_vars: HTTPVariables = []
    for var in vars_:
        value = var[1]
        if var[0] == "hostgroup":
            filtered_vars.append(("opthost_group", value))
            continue
        if var[0] == "servicegroup":
            filtered_vars.append(("optservice_group", value))
            continue
        filtered_vars.append(var)
    return filtered_vars


def _translate_filters(visual: Visual) -> Callable[[str], str]:
    if datasource_name := visual.get("datasource"):
        datasource = data_source_registry[datasource_name]()  # type: ignore[index]
        link_filters = datasource.link_filters
        return lambda x: link_filters.get(x, x)
    return lambda x: x


def get_linked_visual_request_vars(
    visual: Visual, singlecontext_request_vars: dict[str, str]
) -> HTTPVariables:
    vars_values: HTTPVariables = []

    filters = visuals.get_single_info_keys(visual["single_infos"])

    for src_filter, dst_filter in zip(filters, map(_translate_filters(visual), filters)):
        try:
            src_var = visuals.get_filter(src_filter).htmlvars[0]
            dst_var = visuals.get_filter(dst_filter).htmlvars[0]
            vars_values.append((dst_var, singlecontext_request_vars[src_var]))
        except KeyError:
            # The information needed for a mandatory filter (single context) is not available.
            # Continue without failing: The target site will show up a warning and ask for the
            # missing information.
            pass

    if "site" in singlecontext_request_vars:
        vars_values.append(("site", singlecontext_request_vars["site"]))
    else:
        # site may already be added earlier from the livestatus row
        add_site_hint = _may_add_site_hint(
            visual["name"],
            info_keys=tuple(visual_info_registry.keys()),
            single_info_keys=tuple(visual["single_infos"]),
            filter_names=tuple(list(dict(vars_values).keys())),
        )

        if add_site_hint and request.var("site"):
            vars_values.append(("site", request.get_ascii_input_mandatory("site")))

    return vars_values


@request_memoize()
def _may_add_site_hint(
    visual_name: str,
    info_keys: SingleInfos,
    single_info_keys: SingleInfos,
    filter_names: tuple[FilterName, ...],
) -> bool:
    """Whether or not the site hint may be set when linking to a visual with the given details"""
    # When there is one non single site info used don't add the site hint
    if [info_key for info_key in single_info_keys if not _is_single_site_info(info_key)]:
        return False

    # Alternatively when the infos allow a site hint it is also needed to skip the site hint based
    # on the filters used by the target visual
    for info_key in info_keys:
        for filter_key in visual_info_registry[info_key]().multiple_site_filters:
            if filter_key in filter_names:
                return False

    # Hack for servicedesc view which is meant to show all services with the given
    # description: Don't add the site filter for this view.
    if visual_name == "servicedesc":
        return False

    return True


def _is_single_site_info(info_key: InfoName) -> bool:
    return visual_info_registry[info_key]().single_site
