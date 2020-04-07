#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Text, Union  # pylint: disable=unused-import
import cmk.gui.watolib as watolib
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.plugins.views import (
    sorter_registry,
    Sorter,
    painter_registry,
    Painter,
)
from cmk.gui.type_defs import Row  # pylint: disable=unused-import


@painter_registry.register
class PainterHostFilename(Painter):
    @property
    def ident(self):
        return "host_filename"

    def title(self, cell):
        return _("Check_MK config filename")

    def short_title(self, cell):
        return _("Filename")

    @property
    def columns(self):
        return ['host_filename']

    def render(self, row, cell):
        return ("tt", row["host_filename"])


# TODO: Extremely bad idea ahead! The return type depends on a combination of
# the values of how and with_links. :-P
def get_wato_folder(row, how, with_links=True):
    # type: (Dict, Text, bool) -> Union[Text, HTML]
    filename = row["host_filename"]
    if not filename.startswith("/wato/") or not filename.endswith("/hosts.mk"):
        return ""
    wato_path = filename[6:-9]
    try:
        title_path = watolib.get_folder_title_path(wato_path, with_links)
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
    current_path = html.request.var("wato_folder")
    if not current_path or not wato_path.startswith(current_path):
        return HTML(" / ").join(title_path)

    depth = current_path.count('/') + 1
    return HTML(" / ").join(title_path[depth:])


def paint_wato_folder(row, how):
    return "", get_wato_folder(row, how)


@painter_registry.register
class PainterWatoFolderAbs(Painter):
    @property
    def ident(self):
        return "wato_folder_abs"

    def title(self, cell):
        return _("WATO folder - complete path")

    def short_title(self, cell):
        return _("WATO folder")

    @property
    def columns(self):
        return ['host_filename']

    @property
    def sorter(self):
        return 'wato_folder_abs'

    def render(self, row, cell):
        return paint_wato_folder(row, "abs")


@painter_registry.register
class PainterWatoFolderRel(Painter):
    @property
    def ident(self):
        return "wato_folder_rel"

    def title(self, cell):
        return _("WATO folder - relative path")

    def short_title(self, cell):
        return _("WATO folder")

    @property
    def columns(self):
        return ['host_filename']

    @property
    def sorter(self):
        return 'wato_folder_rel'

    def render(self, row, cell):
        return paint_wato_folder(row, "rel")


@painter_registry.register
class PainterWatoFolderPlain(Painter):
    @property
    def ident(self):
        return "wato_folder_plain"

    def title(self, cell):
        return _("WATO folder - just folder name")

    def short_title(self, cell):
        return _("WATO folder")

    @property
    def columns(self):
        return ['host_filename']

    @property
    def sorter(self):
        return 'wato_folder_plain'

    def render(self, row, cell):
        return paint_wato_folder(row, "plain")


def cmp_wato_folder(r1, r2, how):
    # type: (Row, Row, str) -> int
    return ((_get_wato_folder_text(r1, how) > _get_wato_folder_text(r2, how)) -
            (_get_wato_folder_text(r1, how) < _get_wato_folder_text(r2, how)))


# NOTE: The funny Text() call is only necessary because of the broken typing of
# get_wato_folder().
def _get_wato_folder_text(r, how):
    # type: (Row, str) -> Text
    return Text(get_wato_folder(r, how, False))


@sorter_registry.register
class SorterWatoFolderAbs(Sorter):
    @property
    def ident(self):
        return "wato_folder_abs"

    @property
    def title(self):
        return _("WATO folder - complete path")

    @property
    def columns(self):
        return ['host_filename']

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, 'abs')


@sorter_registry.register
class SorterWatoFolderRel(Sorter):
    @property
    def ident(self):
        return "wato_folder_rel"

    @property
    def title(self):
        return _("WATO folder - relative path")

    @property
    def columns(self):
        return ['host_filename']

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, 'rel')


@sorter_registry.register
class SorterWatoFolderPlain(Sorter):
    @property
    def ident(self):
        return "wato_folder_plain"

    @property
    def title(self):
        return _("WATO folder - just folder name")

    @property
    def columns(self):
        return ['host_filename']

    def cmp(self, r1, r2):
        return cmp_wato_folder(r1, r2, 'plain')
