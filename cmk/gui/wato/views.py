#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.painter.v0.base import Cell, Painter
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.html import HTML
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.sorter import Sorter
from cmk.gui.watolib.hosts_and_folders import (
    get_folder_title_path,
    get_folder_title_path_with_links,
)


class PainterHostFilename(Painter):
    @property
    def ident(self) -> str:
        return "host_filename"

    def title(self, cell):
        return _("Checkmk config filename")

    def short_title(self, cell):
        return _("Filename")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("tt", row["host_filename"])


# TODO: Extremely bad idea ahead! The return type depends on a combination of
# the values of how and with_links. :-P
def get_wato_folder(row: Row, how: str, with_links: bool = True, *, request: Request) -> str | HTML:
    filename = row["host_filename"]
    if not filename.startswith("/wato/") or not filename.endswith("/hosts.mk"):
        return ""
    wato_path = filename[6:-9]
    try:
        title_path: list[str] | list[HTML] = (
            get_folder_title_path_with_links(wato_path)
            if with_links
            else get_folder_title_path(wato_path)
        )
    except MKGeneralException:
        # happens when a path can not be resolved using the local Setup.
        # e.g. when having an independent site with different folder
        # hierarchy added to the GUI.
        # Display the raw path rather than the exception text.
        title_path = wato_path.split("/")
    except Exception as e:
        return "%s" % e

    if how == "plain":
        return title_path[-1]
    if how == "abs":
        return HTML(" / ").join(title_path)
    # We assume that only hosts are show, that are below the current Setup path.
    # If not then better output absolute path then wrong path.
    current_path = request.var("wato_folder")
    if not current_path or not wato_path.startswith(current_path):
        return HTML(" / ").join(title_path)

    depth = current_path.count("/") + 1
    return HTML(" / ").join(title_path[depth:])


def paint_wato_folder(row: Row, how: str, *, request: Request) -> CellSpec:
    return "", get_wato_folder(row, how, request=request)


class PainterWatoFolderAbs(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_abs"

    def title(self, cell):
        return _("Folder - complete path")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_abs"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_wato_folder(row, "abs", request=self.request)


class PainterWatoFolderRel(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_rel"

    def title(self, cell):
        return _("Folder - relative path")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_rel"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_wato_folder(row, "rel", request=self.request)


class PainterWatoFolderPlain(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_plain"

    def title(self, cell):
        return _("Folder - just folder name")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_plain"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_wato_folder(row, "plain", request=self.request)


def cmp_wato_folder(r1: Row, r2: Row, how: str, *, request: Request) -> int:
    return (
        _get_wato_folder_text(r1, how, request=request)
        > _get_wato_folder_text(r2, how, request=request)
    ) - (
        _get_wato_folder_text(r1, how, request=request)
        < _get_wato_folder_text(r2, how, request=request)
    )


# NOTE: The funny str() call is only necessary because of the broken typing of
# get_wato_folder().
def _get_wato_folder_text(r: Row, how: str, *, request: Request) -> str:
    return str(get_wato_folder(r, how, False, request=request))


class SorterWatoFolderAbs(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_abs"

    @property
    def title(self) -> str:
        return _("Folder - complete path")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return cmp_wato_folder(r1, r2, "abs", request=self.request)


class SorterWatoFolderRel(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_rel"

    @property
    def title(self) -> str:
        return _("Folder - relative path")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return cmp_wato_folder(r1, r2, "rel", request=self.request)


class SorterWatoFolderPlain(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_plain"

    @property
    def title(self) -> str:
        return _("Folder - just folder name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_filename"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return cmp_wato_folder(r1, r2, "plain", request=self.request)
