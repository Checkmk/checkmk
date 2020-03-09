#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Union, Tuple, List, Text  # pylint: disable=unused-import
import six

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.type_defs import PermissionName  # pylint: disable=unused-import
from .context_buttons import global_buttons

NewMode = Union[None, bool, str]


class WatoMode(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self):
        # type: () -> None
        super(WatoMode, self).__init__()
        self._from_vars()

    @classmethod
    @abc.abstractmethod
    def permissions(cls):
        # type: () -> List[PermissionName]
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
        # type: () -> None
        """Override this method to set mode specific attributes based on the
        given HTTP variables."""
        pass

    def title(self):
        # type: () -> Text
        return _("(Untitled module)")

    def buttons(self):
        # type: () -> None
        global_buttons()

    def action(self):
        # type: () -> Union[NewMode, Tuple[NewMode, Text]]
        pass

    def page(self):
        # type: () -> None
        html.show_message(_("(This module is not yet implemented)"))

    def handle_page(self):
        # type: () -> None
        return self.page()
