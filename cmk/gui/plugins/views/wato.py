#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import Painter, painter_registry, Sorter, sorter_registry
from cmk.gui.type_defs import Row
from cmk.gui.utils.html import HTML
from cmk.gui.watolib.hosts_and_folders import get_folder_title_path


@painter_registry.register
class PainterHostFilename(Painter):
    @property
    def ident(self) -> str:
        return "host_filename"

    def title(self, cell):
        return _("Checkmk config filename")

    def short_title(self, cell):
        return _("Filename")

    @property
    def columns(self):
        return ["host_filename"]

    def render(self, row, cell):
        return ("tt", row["host_filename"])


# TODO: Extremely bad idea ahead! The return type depends on a combination of
# the values of how and with_links. :-P
def get_wato_folder(row: Dict, how: str, with_links: bool = True) -> Union[str, HTML]:
    filename = row["host_filename"]
    if not filename.startswith("/wato/") or not filename.endswith("/hosts.mk"):
        return ""
    wato_path = filename[6:-9]
    try:
        title_path = get_folder_title_path(wato_path, with_links)
    except MKGeneralException:
        # happens when a path can not be resolved using the local WATO.
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
    # We assume that only hosts are show, that are below the current WATO path.
    # If not then better output absolute path then wrong path.
    current_path = request.var("wato_folder")
    if not current_path or not wato_path.startswith(current_path):
        return HTML(" / ").join(title_path)

    depth = current_path.count("/") + 1
    return HTML(" / ").join(title_path[depth:])


def paint_wato_folder(row, how):
    return "", get_wato_folder(row, how)


@painter_registry.register
class PainterWatoFolderAbs(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_abs"

    def title(self, cell):
        return _("Folder - complete path")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self):
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_abs"

    def render(self, row, cell):
        return paint_wato_folder(row, "abs")


@painter_registry.register
class PainterWatoFolderRel(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_rel"

    def title(self, cell):
        return _("Folder - relative path")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self):
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_rel"

    def render(self, row, cell):
        return paint_wato_folder(row, "rel")


@painter_registry.register
class PainterWatoFolderPlain(Painter):
    @property
    def ident(self) -> str:
        return "wato_folder_plain"

    def title(self, cell):
        return _("Folder - just folder name")

    def short_title(self, cell):
        return _("Folder")

    @property
    def columns(self):
        return ["host_filename"]

    @property
    def sorter(self):
        return "wato_folder_plain"

    def render(self, row, cell):
        return paint_wato_folder(row, "plain")


def cmp_wato_folder(r1: Row, r2: Row, how: str) -> int:
    return (_get_wato_folder_text(r1, how) > _get_wato_folder_text(r2, how)) - (
        _get_wato_folder_text(r1, how) < _get_wato_folder_text(r2, how)
    )


# NOTE: The funny str() call is only necessary because of the broken typing of
# get_wato_folder().
def _get_wato_folder_text(r: Row, how: str) -> str:
    return str(get_wato_folder(r, how, False))


@sorter_registry.register
class SorterWatoFolderAbs(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_abs"

    @property
    def title(self):
        return _("Folder - complete path")

    @property
    def columns(self):
        return ["host_filename"]

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, "abs")


@sorter_registry.register
class SorterWatoFolderRel(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_rel"

    @property
    def title(self):
        return _("Folder - relative path")

    @property
    def columns(self):
        return ["host_filename"]

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, "rel")


@sorter_registry.register
class SorterWatoFolderPlain(Sorter):
    @property
    def ident(self) -> str:
        return "wato_folder_plain"

    @property
    def title(self):
        return _("Folder - just folder name")

    @property
    def columns(self):
        return ["host_filename"]

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, "plain")
