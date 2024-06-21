#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Iterator

from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.type_defs import Choices, HTTPVariables, Rows, SingleInfos, Visual, VisualContext
from cmk.gui.view_utils import get_labels


class VisualType(abc.ABC):
    """Base class for all filters"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def ident_attr(self) -> str:
        """The name of the attribute that is used to identify a visual of this type"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def multicontext_links(self) -> bool:
        """Whether or not to show context buttons even if not single infos present"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def plural_title(self) -> str:
        """The plural title to use in the GUI"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def show_url(self) -> str:
        """The URL filename that can be used to show visuals of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_visual_handler(
        self,
        target_visual_name: str,
        add_type: str,
        context: VisualContext | None,
        parameters: dict,
    ) -> None:
        """The function to handle adding the given visual to the given visual of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        """List of visual choices another visual of the given type can be added to"""
        raise NotImplementedError()

    @abc.abstractmethod
    def load_handler(self) -> None:
        """Load all visuals of this type"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def permitted_visuals(self) -> dict:
        """Get the permitted visuals of this type"""
        raise NotImplementedError()

    @property
    def choices(self) -> Choices:
        return [(k, v["title"]) for k, v in self.permitted_visuals.items()]

    def link_from(
        self,
        linking_view_single_infos: SingleInfos,
        linking_view_rows: Rows,
        visual: Visual,
        context_vars: HTTPVariables,
    ) -> bool:
        """Dynamically show/hide links to other visuals (e.g. reports, dashboards, views) from views

        This method uses the conditions read from the "link_from" attribute of a given visual to
        decide whether or not the given linking_view should show a link to the given visual.

        The decision can be made based on the given context_vars, linking_view definition and
        linking_view_rows. Currently there is only a small set of conditions implemented here.

        single_infos: Only link when the given list of single_infos match.
        host_labels: Only link when the given host labels match.

        Example: The visual with this definition will only be linked from host detail pages of hosts
        that are Checkmk servers.

        'link_from': {
            'single_infos': ["host"],
            'host_labels': {
                'cmk/check_mk_server': 'yes'
            }
        }
        """
        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        single_info_condition = link_from.get("single_infos")
        if single_info_condition and not set(single_info_condition).issubset(
            linking_view_single_infos
        ):
            return False  # Not matching required single infos

        # Currently implemented very specific for the cases we need at the moment. Build something
        # more generic once we need it.
        if single_info_condition != ["host"]:
            raise NotImplementedError()

        if not linking_view_rows:
            return False  # Unknown host, no linking

        # In case we have rows of a single host context we only have a single row that holds the
        # host information. In case we have multiple rows, we normally have service rows which
        # all hold the same host information in their host columns.
        row = linking_view_rows[0]

        # Exclude by host labels
        host_labels = get_labels(row, "host")
        for label_group_id, label_value in link_from.get("host_labels", {}).items():
            if host_labels.get(label_group_id) != label_value:
                return False

        return True
