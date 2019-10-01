#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
from typing import List  # pylint: disable=unused-import
import six

from cmk.gui.i18n import _
from cmk.gui.globals import html
from .context_buttons import global_buttons


class WatoMode(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self):
        super(WatoMode, self).__init__()
        self._from_vars()

    @classmethod
    @abc.abstractmethod
    def permissions(cls):
        # type: () -> List[str]
        """permissions = None -> every user can use this mode, permissions
        are checked by the mode itself. Otherwise the user needs at
        least wato.use and - if he makes actions - wato.edit. Plus wato.*
        for each permission in the list."""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def name(cls):
        # type: () -> str
        """Wato wide unique mode name which is used to access this mode"""
        raise NotImplementedError("%s misses name()" % cls.__name__)

    def _from_vars(self):
        """Override this method to set mode specific attributes based on the
        given HTTP variables."""
        pass

    def title(self):
        return _("(Untitled module)")

    def buttons(self):
        global_buttons()

    def action(self):
        pass

    def page(self):
        html.message(_("(This module is not yet implemented)"))

    def handle_page(self):
        return self.page()
