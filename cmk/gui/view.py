#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from livestatus import SiteId

from cmk.utils.type_defs import HostName, ServiceName

import cmk.gui.pagetypes as pagetypes
import cmk.gui.visuals as visuals
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_topic_breadcrumb
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.type_defs import (
    ColumnSpec,
    FilterName,
    HTTPVariables,
    SorterSpec,
    ViewProcessTracking,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.view_breadcrumbs import make_host_breadcrumb, make_service_breadcrumb
from cmk.gui.views.data_source import ABCDataSource, data_source_registry
from cmk.gui.views.layout import Layout, layout_registry
from cmk.gui.views.painter.v0.base import Cell, JoinCell, painter_exists
from cmk.gui.views.sort_url import compute_sort_url_parameter
from cmk.gui.views.sorter import sorter_registry, SorterEntry
from cmk.gui.visuals import view_title


class View:
    """Manages processing of a single view, e.g. during rendering"""

    def __init__(self, view_name: str, view_spec: ViewSpec, context: VisualContext) -> None:
        super().__init__()
        self.name = view_name
        self.spec = view_spec
        self.context: VisualContext = context
        self._row_limit: int | None = None
        self._only_sites: list[SiteId] | None = None
        self._user_sorters: list[SorterSpec] | None = None
        self._want_checkboxes: bool = False
        self._warning_messages: list[str] = []
        self.process_tracking = ViewProcessTracking()

    @property
    def datasource(self) -> ABCDataSource:
        try:
            return data_source_registry[self.spec["datasource"]]()
        except KeyError:
            if self.spec["datasource"].startswith("mkeventd_"):
                raise MKUserError(
                    None,
                    _(
                        "The Event Console view '%s' can not be rendered. The Event Console is possibly "
                        "disabled."
                    )
                    % self.name,
                )
            raise MKUserError(
                None,
                _(
                    "The view '%s' using the datasource '%s' can not be rendered "
                    "because the datasource does not exist."
                )
                % (self.name, self.datasource),
            )

    @property
    def row_cells(self) -> list[Cell]:
        """Regular cells are displaying information about the rows of the type the view is about"""
        cells: list[Cell] = []
        for e in self.spec["painters"]:
            if not painter_exists(e):
                continue

            if (col_type := e.column_type) in ["join_column", "join_inv_column"]:
                cells.append(JoinCell(e, self._compute_sort_url_parameter(e)))
            elif col_type == "column":
                cells.append(Cell(e, self._compute_sort_url_parameter(e)))
            else:
                raise NotImplementedError()

        return cells

    @property
    def group_cells(self) -> list[Cell]:
        """Group cells are displayed as titles of grouped rows"""
        return [
            Cell(e, self._compute_sort_url_parameter(e))
            for e in self.spec["group_painters"]
            if painter_exists(e)
        ]

    @property
    def join_cells(self) -> list[JoinCell]:
        """Join cells are displaying information of a joined source (e.g.service data on host views)"""
        return [x for x in self.row_cells if isinstance(x, JoinCell)]

    @property
    def sorters(self) -> list[SorterEntry]:
        """Returns the list of effective sorters to be used to sort the rows of this view"""
        return self._get_sorter_entries(
            self.user_sorters if self.user_sorters else self.spec["sorters"]
        )

    def _compute_sort_url_parameter(self, painter: ColumnSpec) -> str | None:
        if not self.spec.get("user_sortable", False):
            return None

        return compute_sort_url_parameter(
            painter.name,
            painter.parameters,
            painter.join_value,
            self.spec["group_painters"],
            self.spec["sorters"],
            self._user_sorters or [],
        )

    def _get_sorter_entries(self, sorter_list: Iterable[SorterSpec]) -> list[SorterEntry]:
        sorters: list[SorterEntry] = []
        for entry in sorter_list:
            sorter = entry.sorter
            sorter_cls = sorter_registry.get(
                sorter[0] if isinstance(sorter, tuple) else sorter, None
            )
            if sorter_cls is None:
                continue  # Skip removed sorters

            sorters.append(
                SorterEntry(
                    sorter=sorter_cls(),
                    negate=entry.negate,
                    join_key=entry.join_key,
                    parameters=sorter[1] if isinstance(sorter, tuple) else None,
                )
            )
        return sorters

    @property
    def row_limit(self):
        return self._row_limit

    @row_limit.setter
    def row_limit(self, row_limit: int | None) -> None:
        self._row_limit = row_limit

    @property
    def only_sites(self) -> list[SiteId] | None:
        """Optional list of sites to query instead of all sites

        This is a performance feature. It is highly recommended to set the only_sites attribute
        whenever it is possible. In the moment it is set a livestatus query is not sent to all
        sites anymore but only to the given list of sites."""
        return self._only_sites

    @only_sites.setter
    def only_sites(self, only_sites: list[SiteId] | None) -> None:
        self._only_sites = only_sites

    # FIXME: The layout should get the view as a parameter by default.
    @property
    def layout(self) -> Layout:
        """Return the HTML layout of the view"""
        if "layout" in self.spec:
            return layout_registry[self.spec["layout"]]()

        raise MKUserError(
            None,
            _(
                "The view '%s' using the layout '%s' can not be rendered "
                "because the layout does not exist."
            )
            % (self.name, self.spec.get("layout")),
        )

    @property
    def user_sorters(self) -> list[SorterSpec] | None:
        """Optional list of sorters to use for rendering the view

        The user may click on the headers of tables to change the default view sorting. In the
        moment the user overrides the sorting configured for the view in self.spec"""
        # TODO: Only process in case the view is user sortable
        return self._user_sorters

    @user_sorters.setter
    def user_sorters(self, user_sorters: list[SorterSpec] | None) -> None:
        self._user_sorters = user_sorters

    @property
    def want_checkboxes(self) -> bool:
        """Whether or not the user that displays this view requests to show the checkboxes"""
        return self._want_checkboxes

    @want_checkboxes.setter
    def want_checkboxes(self, want_checkboxes: bool) -> None:
        self._want_checkboxes = want_checkboxes

    @property
    def checkboxes_enforced(self) -> bool:
        """Whether or not the view is configured to always show checkboxes"""
        return self.spec.get("force_checkboxes", False)

    @property
    def checkboxes_displayed(self) -> bool:
        """Whether or not to display the checkboxes in the current view"""
        return self.layout.can_display_checkboxes and (
            self.checkboxes_enforced or self.want_checkboxes
        )

    @property
    def painter_options(self) -> Sequence[str]:
        """Provides the painter options to be used for this view"""
        options: set[str] = set()

        for cell in self.group_cells + self.row_cells:
            options.update(cell.painter_options())

        options.update(self.layout.painter_options)

        # Mandatory options for all views (if permitted)
        if display_options.enabled(display_options.O):
            if display_options.enabled(display_options.R) and user.may(
                "general.view_option_refresh"
            ):
                options.add("refresh")

            if user.may("general.view_option_columns"):
                options.add("num_columns")

        return sorted(options)

    def breadcrumb(self) -> Breadcrumb:
        """Render the breadcrumb for the current view

        In case of views we not only have a hierarchy of

        1. main menu
        2. main menu topic

        We also have a hierarchy between some of the views (see _host_hierarchy_breadcrumb).  But
        this is not the case for all views. A lot of the views are direct children of the topic
        level.
        """

        # View without special hierarchy
        if "host" not in self.spec["single_infos"] or "host" in self.missing_single_infos:
            request_vars: HTTPVariables = [("view_name", self.name)]
            request_vars += list(
                visuals.get_singlecontext_vars(self.context, self.spec["single_infos"]).items()
            )

            breadcrumb = make_topic_breadcrumb(
                mega_menu_registry.menu_monitoring(),
                pagetypes.PagetypeTopics.get_topic(self.spec["topic"]).title(),
            )
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec, self.context),
                    url=makeuri_contextless(request, request_vars),
                )
            )
            return breadcrumb

        # Now handle the views within the host view hierarchy
        return self._host_hierarchy_breadcrumb()

    def _host_hierarchy_breadcrumb(self) -> Breadcrumb:
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
        host_name = self.context["host"]["host"]
        breadcrumb = make_host_breadcrumb(HostName(host_name))

        if self.name == "host":
            # In case we are on the host homepage, we have the final breadcrumb
            return breadcrumb

        # 3a) level: other single host pages
        if "service" not in self.spec["single_infos"]:
            # All other single host pages are right below the host home page
            breadcrumb.append(
                BreadcrumbItem(
                    title=view_title(self.spec, self.context),
                    url=makeuri_contextless(
                        request,
                        [("view_name", self.name), ("host", host_name)],
                    ),
                )
            )
            return breadcrumb

        breadcrumb = make_service_breadcrumb(
            HostName(host_name), ServiceName(self.context["service"]["service"])
        )

        if self.name == "service":
            # In case we are on the service home page, we have the final breadcrumb
            return breadcrumb

        # All other single service pages are right below the host home page
        breadcrumb.append(
            BreadcrumbItem(
                title=view_title(self.spec, self.context),
                url=makeuri_contextless(
                    request,
                    [
                        ("view_name", self.name),
                        ("host", host_name),
                        ("service", self.context["service"]["service"]),
                    ],
                ),
            )
        )

        return breadcrumb

    @property
    def missing_single_infos(self) -> set[FilterName]:
        """Return the missing single infos a view requires"""
        missing_single_infos = visuals.get_missing_single_infos(
            self.spec["single_infos"], self.context
        )

        # Special hack for the situation where host group views link to host views: The host view uses
        # the datasource "hosts" which does not have the "hostgroup" info, but is configured to have a
        # single_info "hostgroup". To make this possible there exists a feature in
        # (ABCDataSource.link_filters, views._patch_view_context) which is a very specific hack. Have a
        # look at the description there.  We workaround the issue here by allowing this specific
        # situation but validating all others.
        #
        # The more correct approach would be to find a way which allows filters of different datasources
        # to have equal names. But this would need a bigger refactoring of the filter mechanic. One
        # day...
        if (
            self.spec["datasource"] in ["hosts", "services"]
            and missing_single_infos == {"hostgroup"}
            and "opthostgroup" in self.context
        ):
            return set()
        if (
            self.spec["datasource"] == "services"
            and missing_single_infos == {"servicegroup"}
            and "optservicegroup" in self.context
        ):
            return set()

        return missing_single_infos

    def add_warning_message(self, message: str) -> None:
        self._warning_messages.append(message)

    @property
    def warning_messages(self) -> list[str]:
        return self._warning_messages
