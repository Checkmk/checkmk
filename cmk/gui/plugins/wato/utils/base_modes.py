#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
        html.show_message(_("(This module is not yet implemented)"))

    def handle_page(self):
        return self.page()
