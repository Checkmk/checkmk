#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import all_painters, Cell, JoinCell, Painter
from cmk.gui.type_defs import (
    ColumnSpec,
    FilterName,
    SorterSpec,
    ViewProcessTracking,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.layout import Layout, layout_registry
from cmk.gui.views.sort_url import compute_sort_url_parameter
from cmk.gui.views.sorter import all_sorters, Sorter, SorterEntry
from cmk.gui.visuals import get_missing_single_infos_group_aware


class View:
    """Manages processing of a single view, e.g. during rendering"""

    def __init__(
        self,
        view_name: str,
        view_spec: ViewSpec,
        context: VisualContext,
        user_permissions: UserPermissions,
    ) -> None:
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
        self.user_permissions = user_permissions

    @property
    def datasource(self) -> ABCDataSource:
        try:
            return data_source_registry[self.spec["datasource"]]()
        except KeyError:
            if self.spec["datasource"].startswith("mkeventd_"):
                raise MKUserError(
                    None,
                    _(
                        "The Event Console view '%s' cannot be rendered. The Event Console might be "
                        "disabled."
                    )
                    % self.name,
                )
            raise MKUserError(
                None,
                _(
                    "The view '%s' using the data source '%s' can not be rendered "
                    "because the data source does not exist."
                )
                % (self.name, self.datasource),
            )

    @property
    def row_cells(self) -> list[Cell]:
        """Regular cells are displaying information about the rows of the type the view is about"""
        cells: list[Cell] = []
        registered_sorters = all_sorters(active_config)
        registered_painters = all_painters(active_config.tags.tag_groups)
        for e in self.spec["painters"]:
            if e.name not in registered_painters:
                continue

            if (col_type := e.column_type) in ["join_column", "join_inv_column"]:
                cells.append(
                    JoinCell(
                        e,
                        self._compute_sort_url_parameter(
                            e, registered_sorters, registered_painters
                        ),
                        registered_painters,
                        self.user_permissions,
                    )
                )
            elif col_type == "column":
                cells.append(
                    Cell(
                        e,
                        self._compute_sort_url_parameter(
                            e, registered_sorters, registered_painters
                        ),
                        registered_painters,
                        self.user_permissions,
                    )
                )
            else:
                raise NotImplementedError()

        return cells

    @property
    def group_cells(self) -> list[Cell]:
        """Group cells are displayed as titles of grouped rows"""
        registered_sorters = all_sorters(active_config)
        registered_painters = all_painters(active_config.tags.tag_groups)
        return [
            Cell(
                e,
                self._compute_sort_url_parameter(e, registered_sorters, registered_painters),
                registered_painters,
                self.user_permissions,
            )
            for e in self.spec["group_painters"]
            if e.name in registered_painters
        ]

    @property
    def join_cells(self) -> list[JoinCell]:
        """Join cells are displaying information of a joined source (e.g.service data on host views)"""
        return [x for x in self.row_cells if isinstance(x, JoinCell)]

    @property
    def sorters(self) -> list[SorterEntry]:
        """Returns the list of effective sorters to be used to sort the rows of this view"""
        registered_sorters = all_sorters(active_config)
        return self._get_sorter_entries(
            self.user_sorters if self.user_sorters else self.spec["sorters"],
            registered_sorters,
        )

    def _compute_sort_url_parameter(
        self,
        painter: ColumnSpec,
        registered_sorters: Mapping[str, Sorter],
        registered_painters: Mapping[str, type[Painter]],
    ) -> str | None:
        if not self.spec.get("user_sortable", False):
            return None

        return compute_sort_url_parameter(
            painter.name,
            painter.parameters,
            painter.join_value,
            self.spec["group_painters"],
            self.spec["sorters"],
            self._user_sorters or [],
            registered_sorters,
            registered_painters,
            self.user_permissions,
        )

    def _get_sorter_entries(
        self,
        sorter_list: Iterable[SorterSpec],
        registered_sorters: Mapping[str, Sorter],
    ) -> list[SorterEntry]:
        sorters: list[SorterEntry] = []
        for entry in sorter_list:
            sorter_spec = entry.sorter
            sorter = registered_sorters.get(
                sorter_spec[0] if isinstance(sorter_spec, tuple) else sorter_spec, None
            )
            if sorter is None:
                continue  # Skip removed sorters

            sorters.append(
                SorterEntry(
                    sorter=sorter,
                    negate=entry.negate,
                    join_key=entry.join_key,
                    parameters=(sorter_spec[1] if isinstance(sorter_spec, tuple) else None),
                )
            )
        return sorters

    @property
    def row_limit(self) -> int | None:
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
                "The view '%s' using the layout '%s' cannot be rendered "
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

            if user.may("general.view_option_columns") and not self.layout.hide_entries_per_row:
                options.add("num_columns")

        return sorted(options)

    @property
    def missing_single_infos(self) -> set[FilterName]:
        """Return the missing single infos a view requires"""
        return get_missing_single_infos_group_aware(
            self.spec["single_infos"], self.context, self.spec["datasource"]
        )

    def add_warning_message(self, message: str) -> None:
        self._warning_messages.append(message)

    @property
    def warning_messages(self) -> list[str]:
        return self._warning_messages
