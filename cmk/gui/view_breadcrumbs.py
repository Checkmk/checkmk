#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName
from cmk.gui import pagetypes, visuals
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import append_site_from_request, makeuri_contextless
from cmk.gui.view import View
from cmk.gui.views.store import get_permitted_views
from cmk.gui.visuals import view_title
from cmk.utils.servicename import ServiceName


def view_breadcrumb(view: View) -> Breadcrumb:
    """Render the breadcrumb for the given view

    In case of views we not only have a hierarchy of

    1. main menu
    2. main menu topic

    We also have a hierarchy between some of the views (see _host_hierarchy_breadcrumb).  But
    this is not the case for all views. A lot of the views are direct children of the topic
    level.
    """

    # View without special hierarchy
    if "host" not in view.spec["single_infos"] or "host" in view.missing_single_infos:
        request_vars: HTTPVariables = [("view_name", view.name)]
        request_vars += list(
            visuals.get_singlecontext_vars(view.context, view.spec["single_infos"]).items()
        )
        request_vars = append_site_from_request(request_vars)

        breadcrumb = make_topic_breadcrumb(
            main_menu_registry.menu_monitoring(),
            pagetypes.PagetypeTopics.get_topic(view.spec["topic"], view.user_permissions).title(),
        )
        breadcrumb.append(
            BreadcrumbItem(
                title=view_title(view.spec, view.context),
                url=makeuri_contextless(request, request_vars),
                id=f"view_{view.name}",
            )
        )
        return breadcrumb

    # Now handle the views within the host view hierarchy
    return _host_hierarchy_breadcrumb(view)


def _host_hierarchy_breadcrumb(view: View) -> Breadcrumb:
    """Realize the host hierarchy breadcrumb

    All hosts
     |
     + host home view
       |
       + host views
       |
       + service home view
         |
         + service views
    """
    try:
        host_name = HostName(view.context["host"]["host"])
    except ValueError:
        raise MKUserError("host", _("Invalid host name"))
    breadcrumb = make_host_breadcrumb(host_name, view.user_permissions)

    if view.name == "host":
        # In case we are on the host homepage, we have the final breadcrumb
        return breadcrumb

    # 3a) level: other single host pages
    if "service" not in view.spec["single_infos"]:
        # All other single host pages are right below the host home page
        breadcrumb.append(
            BreadcrumbItem(
                title=view_title(view.spec, view.context),
                url=makeuri_contextless(
                    request,
                    append_site_from_request(
                        [
                            ("view_name", view.name),
                            ("host", str(host_name)),
                        ]
                    ),
                ),
                id=f"view_{view.name}",
            )
        )
        return breadcrumb

    breadcrumb = make_service_breadcrumb(
        host_name, ServiceName(view.context["service"]["service"]), view.user_permissions
    )

    if view.name == "service":
        # In case we are on the service home page, we have the final breadcrumb
        return breadcrumb

    # All other single service pages are right below the host home page
    breadcrumb.append(
        BreadcrumbItem(
            title=view_title(view.spec, view.context),
            url=makeuri_contextless(
                request,
                append_site_from_request(
                    [
                        ("view_name", view.name),
                        ("host", str(host_name)),
                        ("service", view.context["service"]["service"]),
                    ]
                ),
            ),
            id=f"view_{view.name}",
        )
    )

    return breadcrumb


def make_service_breadcrumb(
    host_name: HostName, service_name: ServiceName, user_permissions: UserPermissions
) -> Breadcrumb:
    breadcrumb = make_host_breadcrumb(host_name, user_permissions)
    breadcrumb.append(_service_breadcrumb(host_name, service_name))
    return breadcrumb


def _service_breadcrumb(host_name: HostName, service_name: ServiceName) -> BreadcrumbItem:
    permitted_views = get_permitted_views()
    if service_view_spec := permitted_views.get("service"):
        return BreadcrumbItem(
            title=view_title(service_view_spec, context={}),
            url=makeuri_contextless(
                request,
                append_site_from_request(
                    [
                        ("view_name", "service"),
                        ("host", host_name),
                        ("service", service_name),
                    ]
                ),
                filename="view.py",
            ),
            id=None,
        )
    # In case of no permission for the service view, use breadcrumb without URL
    return BreadcrumbItem(title="Service", url=None, id=None)


def make_host_breadcrumb(host_name: HostName, user_permissions: UserPermissions) -> Breadcrumb:
    """Create the breadcrumb down to the "host home page" level"""
    permitted_views = get_permitted_views()
    allhosts_view_spec = permitted_views["allhosts"]

    breadcrumb = make_topic_breadcrumb(
        main_menu_registry.menu_monitoring(),
        PagetypeTopics.get_topic(allhosts_view_spec["topic"], user_permissions).title(),
    )

    # 1. level: list of all hosts
    breadcrumb.append(
        BreadcrumbItem(
            title=_u(str(allhosts_view_spec["title"])),
            url=makeuri_contextless(
                request,
                [("view_name", "allhosts")],
                filename="view.py",
            ),
            id=None,
        )
    )

    # 2. Level: hostname (url to status of host)
    breadcrumb.append(
        BreadcrumbItem(
            title=host_name,
            url=makeuri_contextless(
                request,
                append_site_from_request([("view_name", "hoststatus"), ("host", host_name)]),
                filename="view.py",
            ),
            id=None,
        )
    )

    # 3. level: host home page
    host_view_spec = permitted_views["host"]
    breadcrumb.append(
        BreadcrumbItem(
            title=view_title(host_view_spec, context={}),
            url=makeuri_contextless(
                request,
                append_site_from_request([("view_name", "host"), ("host", host_name)]),
                filename="view.py",
            ),
            id=None,
        )
    )

    return breadcrumb
