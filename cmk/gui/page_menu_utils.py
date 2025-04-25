#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import cmk.ccc.version as cmk_version
from cmk.ccc.user import UserId

from cmk.utils import paths

from cmk.gui import pagetypes, visuals
from cmk.gui.bi import is_part_of_aggregation
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_external_link,
    make_simple_link,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.type_defs import InfoName, Rows, SingleInfos, Visual
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.view import View
from cmk.gui.visual_link import get_linked_visual_request_vars, make_linked_visual_url
from cmk.gui.visuals import view_title
from cmk.gui.visuals.info import visual_info_registry, VisualInfo
from cmk.gui.visuals.type import visual_type_registry, VisualType


def get_context_page_menu_dropdowns(view: View, rows: Rows, mobile: bool) -> list[PageMenuDropdown]:
    """For the given visual find other visuals to link to

    Based on the (single_infos and infos of the data source) we have different categories,
    for example a single host view has the following categories:

    - Single host
    - Multiple hosts

    Each of these gets a dedicated dropdown which contain entries to the visuals that
    share this context. The entries are grouped by the topics defined by the visuals.
    """
    dropdowns = []

    topics = {p.name(): p for p in pagetypes.PagetypeTopics.load().permitted_instances_sorted()}

    # First gather a flat list of all visuals to be linked to
    singlecontext_request_vars = visuals.get_singlecontext_vars(
        view.context, view.spec["single_infos"]
    )
    # Reports are displayed by separate dropdown (Export > Report)
    linked_visuals = list(
        _collect_linked_visuals(
            view, rows, singlecontext_request_vars, mobile, visual_types=["views", "dashboards"]
        )
    )

    # Now get the "info+single object" combinations to show dropdown menus for
    for info_name, is_single_info in _get_relevant_infos(view):
        ident = "{}_{}".format(info_name, "single" if is_single_info else "multiple")
        info = visual_info_registry[info_name]()

        dropdown_visuals = _get_visuals_for_page_menu_dropdown(linked_visuals, info, is_single_info)

        # Special hack for host setup and parent/child topology links
        host_setup_topic = []
        parent_child_topic = []
        service_setup_topic = []
        if info_name == "host" and is_single_info:
            host_setup_topic = _page_menu_host_setup_topic(view)
            parent_child_topic = _page_menu_networking_topic(view)
        elif info_name == "service" and is_single_info:
            service_setup_topic = _page_menu_service_setup_topic(view)

        dropdowns.append(
            PageMenuDropdown(
                name=ident,
                title=info.title if is_single_info else info.title_plural,
                topics=host_setup_topic
                + service_setup_topic
                + parent_child_topic
                + list(
                    _get_context_page_menu_topics(
                        view,
                        info,
                        is_single_info,
                        topics,
                        dropdown_visuals,
                        singlecontext_request_vars,
                        mobile,
                    )
                ),
            )
        )

    return dropdowns


def _get_context_page_menu_topics(
    view: View,
    info: VisualInfo,
    is_single_info: bool,
    topics: dict[str, pagetypes.PagetypeTopics],
    dropdown_visuals: Iterator[tuple[VisualType, Visual]],
    singlecontext_request_vars: dict[str, str],
    mobile: bool,
) -> Iterator[PageMenuTopic]:
    """Create the page menu topics for the given dropdown from the flat linked visuals list"""
    by_topic: dict[pagetypes.PagetypeTopics, list[PageMenuEntry]] = {}

    host_name = singlecontext_request_vars.get("host")
    service_description = singlecontext_request_vars.get("service")

    for visual_type, visual in sorted(
        dropdown_visuals, key=lambda i: (i[1]["sort_index"], i[1]["title"])
    ):
        if visual.get("topic") == "bi" and (
            host_name is not None
            and not is_part_of_aggregation(host_name, service_description or "")
        ):
            continue

        if (
            visual.get("name", "").startswith("topology_")
            and visual.get("owner", "") == UserId.builtin()
        ):
            # Don't show network topology views
            continue

        try:
            topic = topics[visual["topic"]]
        except KeyError:
            if "other" not in topics:
                raise MKUserError(
                    None,
                    _(
                        "No permission for fallback topic 'Other'. Please contact your administrator."
                    ),
                )
            topic = topics["other"]

        entry = _make_page_menu_entry_for_visual(
            visual_type, visual, singlecontext_request_vars, mobile
        )

        by_topic.setdefault(topic, []).append(entry)

    if user.may("pagetype_topic.history"):
        if availability_entry := _get_availability_entry(view, info, is_single_info):
            by_topic.setdefault(topics["history"], []).append(availability_entry)

        if combined_graphs_entry := _get_combined_graphs_entry(view, info, is_single_info):
            by_topic.setdefault(topics["history"], []).append(combined_graphs_entry)

    # Return the sorted topics
    for topic, entries in sorted(by_topic.items(), key=lambda e: (e[0].sort_index(), e[0].title())):
        yield PageMenuTopic(
            title=topic.title(),
            entries=entries,
        )


def _get_visuals_for_page_menu_dropdown(
    linked_visuals: list[tuple[VisualType, Visual]], info: VisualInfo, is_single_info: bool
) -> Iterator[tuple[VisualType, Visual]]:
    """Extract the visuals for the given dropdown from the flat linked visuals list"""
    for visual_type, visual in linked_visuals:
        if is_single_info and info.ident in visual["single_infos"]:
            yield visual_type, visual
            continue


def _get_relevant_infos(view: View) -> list[tuple[InfoName, bool]]:
    """Gather the infos that are relevant for this view"""
    dropdowns = [(info_name, True) for info_name in view.spec["single_infos"]]
    dropdowns += [(info_name, False) for info_name in view.datasource.infos]
    return dropdowns


def collect_context_links(
    view: View, rows: Rows, mobile: bool, visual_types: SingleInfos
) -> Iterator[PageMenuEntry]:
    """Collect all visuals that share a context with visual. For example
    if a visual has a host context, get all relevant visuals."""
    # compute collections of set single context related request variables needed for this visual
    singlecontext_request_vars = visuals.get_singlecontext_vars(
        view.context, view.spec["single_infos"]
    )

    for visual_type, visual in _collect_linked_visuals(
        view, rows, singlecontext_request_vars, mobile, visual_types
    ):
        yield _make_page_menu_entry_for_visual(
            visual_type,
            visual,
            singlecontext_request_vars,
            mobile,
            external_link=True,
        )


def _collect_linked_visuals(
    view: View,
    rows: Rows,
    singlecontext_request_vars: dict[str, str],
    mobile: bool,
    visual_types: SingleInfos,
) -> Iterator[tuple[VisualType, Visual]]:
    for type_name in visual_type_registry.keys():
        if type_name in visual_types:
            yield from _collect_linked_visuals_of_type(
                type_name, view, rows, singlecontext_request_vars, mobile
            )


def _collect_linked_visuals_of_type(
    type_name: str, view: View, rows: Rows, singlecontext_request_vars: dict[str, str], mobile: bool
) -> Iterator[tuple[VisualType, Visual]]:
    visual_type = visual_type_registry[type_name]()
    visual_type.load_handler()
    available_visuals = visual_type.permitted_visuals

    for visual in sorted(available_visuals.values(), key=lambda x: x.get("name") or ""):
        if visual == view.spec:
            continue

        if visual.get("hidebutton", False):
            continue  # this visual does not want a button to be displayed

        if not mobile and visual.get("mobile") or mobile and not visual.get("mobile"):
            continue

        # For dashboards and views we currently only show a link button,
        # if the target dashboard/view shares a single info with the
        # current visual.
        if not visual["single_infos"] and not visual_type.multicontext_links:
            continue  # skip non single visuals for dashboard, views

        # We can show a button only if all single contexts of the
        # target visual are known currently
        has_single_contexts = all(
            var in singlecontext_request_vars
            for var in visuals.get_single_info_keys(visual["single_infos"])
        )
        if not has_single_contexts:
            continue

        # Optional feature of visuals: Make them dynamically available as links or not.
        # This has been implemented for HW/SW Inventory views which are often useless when a host
        # has no such information available. For example the "Oracle Tablespaces" inventory view
        # is useless on hosts that don't host Oracle databases.
        vars_values = get_linked_visual_request_vars(visual, singlecontext_request_vars)
        if not visual_type.link_from(view.spec["single_infos"], rows, visual, vars_values):
            continue

        yield visual_type, visual


def _make_page_menu_entry_for_visual(
    visual_type: VisualType,
    visual: Visual,
    singlecontext_request_vars: dict[str, str],
    mobile: bool,
    external_link: bool = False,
) -> PageMenuEntry:
    url: str = make_linked_visual_url(visual_type, visual, singlecontext_request_vars, mobile)
    link: PageMenuLink = make_external_link(url) if external_link else make_simple_link(url)
    return PageMenuEntry(
        title=str(visual["title"]),
        icon_name=visual.get("icon") or "trans",
        item=link,
        name="cb_" + visual["name"],
        is_show_more=visual.get("is_show_more", False),
    )


def _get_availability_entry(
    view: View, info: VisualInfo, is_single_info: bool
) -> PageMenuEntry | None:
    """Detect whether or not to add an availability link to the dropdown currently being rendered

    In which dropdown to expect the "show availability for current view" link?

    host, service -> service
    host, services -> services
    hosts, services -> services
    hosts, service -> services

    host -> host
    hosts -> hosts

    aggr -> aggr
    aggrs -> aggrs
    """
    if not _show_current_view_availability_context_button(view):
        return None

    if not _show_in_current_dropdown(view, info.ident, is_single_info):
        return None

    return PageMenuEntry(
        title=_("Availability"),
        icon_name="availability",
        item=make_simple_link(
            makeuri(request, [("mode", "availability")], delvars=["show_checkboxes", "selection"])
        ),
        is_enabled=not view.missing_single_infos,
        disabled_tooltip=(
            _("Missing required context information") if view.missing_single_infos else None
        ),
    )


def _show_current_view_availability_context_button(view: View) -> bool:
    if not user.may("general.see_availability"):
        return False

    if "aggr" in view.datasource.infos:
        return True

    return view.datasource.ident in ["hosts", "services"]


def _get_combined_graphs_entry(
    view: View, info: VisualInfo, is_single_info: bool
) -> PageMenuEntry | None:
    """Detect whether or not to add a combined graphs link to the dropdown currently being rendered

    In which dropdown to expect the "All metrics of same type in one graph" link?

    """
    if not _show_combined_graphs_context_button(view):
        return None

    if not _show_in_current_dropdown(view, info.ident, is_single_info):
        return None

    return PageMenuEntry(
        title=_("All metrics of same type in one graph"),
        icon_name="graph",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("single_infos", ",".join(view.spec["single_infos"])),
                    ("datasource", view.datasource.ident),
                    ("view_title", view_title(view.spec, view.context)),
                    *visuals.context_to_uri_vars(
                        visuals.active_context_from_request(
                            view.datasource.infos,
                            view.context,
                        )
                    ),
                ],
                filename="combined_graphs.py",
            )
        ),
    )


def _show_combined_graphs_context_button(view: View) -> bool:
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE:
        return False

    if view.name == "service":
        return False

    return view.datasource.ident in ["hosts", "services", "hostsbygroup", "servicesbygroup"]


def _show_in_current_dropdown(view: View, info_name: InfoName, is_single_info: bool) -> bool:
    if info_name == "aggr_group":
        return False  # Not showing for groups

    if info_name == "service" and is_single_info:
        return sorted(view.spec["single_infos"]) == ["host", "service"]

    matches_datasource = _dropdown_matches_datasource(info_name, view.datasource)

    if info_name == "service" and not is_single_info:
        return "service" not in view.spec["single_infos"] and matches_datasource

    if is_single_info:
        return view.spec["single_infos"] == [info_name] and matches_datasource

    return info_name not in view.spec["single_infos"] and matches_datasource


def _dropdown_matches_datasource(info_name: InfoName, datasource: ABCDataSource) -> bool:
    if info_name == "host":
        return datasource.ident == "hosts"
    if info_name == "service":
        return datasource.ident == "services"
    if info_name in ["hostgroup", "servicegroup"]:
        return False
    if info_name == "aggr":
        return "aggr" in datasource.infos

    # This is not generic enough. Generalize once we hit this
    raise ValueError(
        f"Can not decide whether or not to show this button: {info_name}, {datasource.ident}"
    )


def _page_menu_networking_topic(view: View) -> list[PageMenuTopic]:
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        return []

    host_name = view.context["host"]["host"]

    return [
        PageMenuTopic(
            title=_("Network monitoring"),
            entries=[
                PageMenuEntry(
                    title=_("Parent/child topology"),
                    icon_name="aggr",
                    item=make_simple_link(
                        makeuri_contextless(
                            request,
                            [("host_name", host_name)],
                            filename="parent_child_topology.py",
                        )
                    ),
                )
            ],
        )
    ]


def _page_menu_host_setup_topic(view: View) -> list[PageMenuTopic]:
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        return []

    if not active_config.wato_enabled:
        return []

    if not user.may("wato.use"):
        return []

    if not user.may("wato.hosts") and not user.may("wato.seeall"):
        return []

    host_name = view.context["host"]["host"]

    return [
        PageMenuTopic(
            title=_("Setup"),
            entries=list(page_menu_entries_host_setup(host_name)),
        )
    ]


def _page_menu_service_setup_topic(view: View) -> list[PageMenuTopic]:
    if "service" not in view.spec["single_infos"] or "service" in view.missing_single_infos:
        return []
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        return []

    if not active_config.wato_enabled:
        return []

    if not user.may("wato.use"):
        return []

    if not user.may("wato.hosts") and not user.may("wato.seeall"):
        return []

    return [
        PageMenuTopic(
            title=_("Setup"),
            entries=list(
                page_menu_entries_service_setup(
                    view.context["host"]["host"], view.context["service"]["service"]
                )
            ),
        )
    ]


def _link_to_host_by_name(host_name: str) -> str:
    """Return an URL to the edit-properties of a host when we just know its name"""
    return makeuri_contextless(
        request,
        [("mode", "edit_host"), ("host", host_name)],
        filename="wato.py",
    )


def page_menu_entries_host_setup(host_name: str) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Host configuration"),
        icon_name={
            "icon": "folder",
            "emblem": "settings",
        },
        item=make_simple_link(_link_to_host_by_name(host_name)),
    )

    yield PageMenuEntry(
        title=_("Run service discovery"),
        icon_name={
            "icon": "services",
            "emblem": "settings",
        },
        item=make_simple_link(
            makeuri_contextless(
                request,
                [("mode", "inventory"), ("host", host_name)],
                filename="wato.py",
            )
        ),
    )

    is_cluster = False
    if is_cluster:
        yield PageMenuEntry(
            title=_("Test connection"),
            icon_name="analysis",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "diag_host"), ("host", host_name)],
                    filename="wato.py",
                )
            ),
        )

    if user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "object_parameters"), ("host", host_name)],
                    filename="wato.py",
                )
            ),
        )

        yield PageMenuEntry(
            title=_("Rules"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [
                        ("mode", "rule_search"),
                        ("filled_in", "search"),
                        ("search_p_ruleset_deprecated", "OFF"),
                        ("search_p_rule_host_list_USE", "ON"),
                        ("search_p_rule_host_list", host_name),
                    ],
                    filename="wato.py",
                )
            ),
        )
    yield PageMenuEntry(
        title=_("Test notifications"),
        icon_name="analysis",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("mode", "test_notifications"),
                    ("host_name", host_name),
                ],
                filename="wato.py",
            )
        ),
    )


def page_menu_entries_service_setup(host_name: str, serivce_name: str) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Test notifications"),
        icon_name="analysis",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("mode", "test_notifications"),
                    ("host_name", host_name),
                    ("service_name", serivce_name),
                    ("test_type", "svc_test"),
                ],
                filename="wato.py",
            )
        ),
    )
