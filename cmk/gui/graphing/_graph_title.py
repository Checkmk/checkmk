#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from cmk.gui.http import Request, request
from cmk.gui.i18n import _u
from cmk.gui.sites import get_alias_of_host
from cmk.gui.utils.urls import makeuri_contextless

from ._graph_display_config import GraphDisplayConfigHTML, GraphDisplayConfigImage
from ._graph_specification import GraphSpecification
from ._graph_templates import TemplateGraphSpecification


@dataclass(frozen=True, kw_only=True)
class TitleElement:
    text: str
    url: str | None


def _render_title_elements_plain(elements: Iterable[str]) -> str:
    return " / ".join(_u(txt) for txt in elements if txt)


# TODO: still relies on the global request object because painters also use this function.
def render_plain_graph_title(
    specification: GraphSpecification,
    graph_title: str,
    display_config: GraphDisplayConfigHTML | GraphDisplayConfigImage,
) -> str:
    return _render_title_elements_plain(
        element.text
        for element in iter_graph_title_elements(
            request, specification, graph_title, display_config
        )
    )


def iter_graph_title_elements(
    request: Request,
    specification: GraphSpecification,
    graph_title: str,
    display_config: GraphDisplayConfigHTML | GraphDisplayConfigImage,
    explicit_title: str | None = None,
) -> Iterator[TitleElement]:
    if not display_config.show_title:
        return

    # Hard override of the graph title. This is e.g. needed for the graph previews
    if explicit_title is not None:
        yield TitleElement(text=explicit_title, url=None)
        return

    if display_config.title_format.plain and graph_title:
        yield TitleElement(text=graph_title, url=None)

    # Only add host/service information for template based graphs
    if not isinstance(specification, TemplateGraphSpecification):
        return

    if display_config.title_format.add_host_name:
        yield TitleElement(
            text=specification.host_name,
            url=makeuri_contextless(
                request,
                [("view_name", "hoststatus"), ("host", specification.host_name)],
                filename="view.py",
            ),
        )

    if display_config.title_format.add_host_alias:
        yield TitleElement(
            text=get_alias_of_host(specification.site, specification.host_name),
            url=makeuri_contextless(
                request,
                [("view_name", "hoststatus"), ("host", specification.host_name)],
                filename="view.py",
            ),
        )

    if (
        display_config.title_format.add_service_description
        and specification.service_description != "_HOST_"
    ):
        yield TitleElement(
            text=specification.service_description,
            url=makeuri_contextless(
                request,
                [
                    ("view_name", "service"),
                    ("host", specification.host_name),
                    ("service", specification.service_description),
                ],
                filename="view.py",
            ),
        )
