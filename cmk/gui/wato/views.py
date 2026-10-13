#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.gui.config import Config, RequestCacheConfig
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter import Cell, InternalPainter, PainterContext
from cmk.gui.type_defs import Row
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.sorter import Sorter
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import RequestCache

from ._folder_titles import FOLDER_TITLES


def _render_host_filename(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("tt", row["host_filename"])


def make_host_filename_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_filename",
        title=_l("Checkmk config file name"),
        short_title=_l("File name"),
        columns=["host_filename"],
        render=_render_host_filename,
    )


# TODO: Extremely bad idea ahead! The return type depends on a combination of
# the values of how and with_links. :-P
def get_wato_folder(
    row: Row,
    how: str,
    with_links: bool = True,
    *,
    request: Request,
    request_cache: RequestCache[RequestCacheConfig],
) -> str | HTML:
    filename = row["host_filename"]
    if not filename.startswith("/wato/") or not filename.endswith("/hosts.mk"):
        return ""
    wato_path = filename[6:-9]
    title_path = request_cache.get(FOLDER_TITLES).title_path(wato_path, with_links)
    if isinstance(title_path, str):
        return title_path

    if how == "plain":
        return title_path[-1]
    if how == "abs":
        return HTML.without_escaping(" / ").join(title_path)
    # We assume that only hosts are show, that are below the current Setup path.
    # If not then better output absolute path then wrong path.
    current_path = request.var("wato_folder")
    if not current_path or not wato_path.startswith(current_path):
        return HTML.without_escaping(" / ").join(title_path)

    depth = current_path.count("/") + 1
    return HTML.without_escaping(" / ").join(title_path[depth:])


def paint_wato_folder(
    row: Row, how: str, *, request: Request, request_cache: RequestCache[RequestCacheConfig]
) -> CellSpec:
    return "", get_wato_folder(row, how, request=request, request_cache=request_cache)


def _render_wato_folder_abs(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_wato_folder(row, "abs", request=context.request, request_cache=cell.request_cache)


def make_wato_folder_abs_painter() -> InternalPainter:
    return InternalPainter(
        ident="wato_folder_abs",
        title=_l("Folder - complete path"),
        short_title=_l("Folder"),
        columns=["host_filename"],
        sorter="wato_folder_abs",
        render=_render_wato_folder_abs,
    )


def _render_wato_folder_rel(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_wato_folder(row, "rel", request=context.request, request_cache=cell.request_cache)


def make_wato_folder_rel_painter() -> InternalPainter:
    return InternalPainter(
        ident="wato_folder_rel",
        title=_l("Folder - relative path"),
        short_title=_l("Folder"),
        columns=["host_filename"],
        sorter="wato_folder_rel",
        render=_render_wato_folder_rel,
    )


def _render_wato_folder_plain(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_wato_folder(
        row, "plain", request=context.request, request_cache=cell.request_cache
    )


def make_wato_folder_plain_painter() -> InternalPainter:
    return InternalPainter(
        ident="wato_folder_plain",
        title=_l("Folder - just folder name"),
        short_title=_l("Folder"),
        columns=["host_filename"],
        sorter="wato_folder_plain",
        render=_render_wato_folder_plain,
    )


def cmp_wato_folder(
    r1: Row, r2: Row, how: str, *, request: Request, request_cache: RequestCache[RequestCacheConfig]
) -> int:
    return (
        _get_wato_folder_text(r1, how, request=request, request_cache=request_cache)
        > _get_wato_folder_text(r2, how, request=request, request_cache=request_cache)
    ) - (
        _get_wato_folder_text(r1, how, request=request, request_cache=request_cache)
        < _get_wato_folder_text(r2, how, request=request, request_cache=request_cache)
    )


# NOTE: The funny str() call is only necessary because of the broken typing of
# get_wato_folder().
def _get_wato_folder_text(
    r: Row, how: str, *, request: Request, request_cache: RequestCache[RequestCacheConfig]
) -> str:
    return str(get_wato_folder(r, how, False, request=request, request_cache=request_cache))


def _sort_wato_folder_abs(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,  # noqa: ARG001
    config: Config,  # noqa: ARG001
    request: Request,
    request_cache: RequestCache[RequestCacheConfig],
) -> int:
    return cmp_wato_folder(r1, r2, "abs", request=request, request_cache=request_cache)


SorterWatoFolderAbs = Sorter(
    ident="wato_folder_abs",
    title=_l("Folder - complete path"),
    columns=["host_filename"],
    sort_function=_sort_wato_folder_abs,
)


def _sort_wato_folder_rel(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,  # noqa: ARG001
    config: Config,  # noqa: ARG001
    request: Request,
    request_cache: RequestCache[RequestCacheConfig],
) -> int:
    return cmp_wato_folder(r1, r2, "rel", request=request, request_cache=request_cache)


SorterWatoFolderRel = Sorter(
    ident="wato_folder_rel",
    title=_l("Folder - relative path"),
    columns=["host_filename"],
    sort_function=_sort_wato_folder_rel,
)


def _sort_wato_folder_plain(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,  # noqa: ARG001
    config: Config,  # noqa: ARG001
    request: Request,
    request_cache: RequestCache[RequestCacheConfig],
) -> int:
    return cmp_wato_folder(r1, r2, "plain", request=request, request_cache=request_cache)


SorterWatoFolderPlain = Sorter(
    ident="wato_folder_plain",
    title=_l("Folder - just folder name"),
    columns=["host_filename"],
    sort_function=_sort_wato_folder_plain,
)
