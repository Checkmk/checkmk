#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Union, Tuple, List, Optional, Type

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.type_defs import PermissionName
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import PageMenu
from cmk.gui.plugins.wato.utils.context_buttons import global_buttons
from cmk.gui.type_defs import MegaMenu
from cmk.gui.main_menu import MegaMenuSetup

NewMode = Union[None, bool, str]
ActionResult = Union[NewMode, Tuple[NewMode, str]]


class WatoMode(metaclass=abc.ABCMeta):
    def __init__(self) -> None:
        super(WatoMode, self).__init__()
        self._from_vars()

    @classmethod
    @abc.abstractmethod
    def permissions(cls) -> List[PermissionName]:
        """permissions = None -> every user can use this mode, permissions
        are checked by the mode itself. Otherwise the user needs at
        least wato.use and - if he makes actions - wato.edit. Plus wato.*
        for each permission in the list."""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        """Wato wide unique mode name which is used to access this mode"""
        raise NotImplementedError("%s misses name()" % cls.__name__)

    @classmethod
    def parent_mode(cls) -> Optional[Type["WatoMode"]]:
        """Reference from a mode to it's parent mode to make the breadcrumb be able to render the
        hierarchy of modes"""
        return None

    def _from_vars(self) -> None:
        """Override this method to set mode specific attributes based on the
        given HTTP variables."""

    def title(self) -> str:
        return _("(Untitled module)")

    # Currently only needed for a special WATO module "user_notifications_p" that
    # is not part of the Setup main menu but the user menu.
    def main_menu(self) -> MegaMenu:
        """Specify the top-level breadcrumb item of this mode"""
        return MegaMenuSetup

    def breadcrumb(self) -> Breadcrumb:
        """Render the breadcrumb to the current mode

        This methods job is to a) gather the breadcrumb from the
        parent modes, b) append it's own part and then return it
        """

        if parent_cls := self.parent_mode():
            # For some reason pylint does not understand that this is a class type
            breadcrumb = parent_cls().breadcrumb()  # pylint: disable=not-callable
        else:
            breadcrumb = Breadcrumb()

        breadcrumb.append(self._breadcrumb_item())

        return breadcrumb

    def _breadcrumb_item(self) -> BreadcrumbItem:
        """Return the breadcrumb item for the current mode"""
        # For the currently active mode use the same link as the "page title click"
        if html.request.get_ascii_input("mode") == self.name():
            breadcrumb_url = "javascript:window.location.reload(false)"
        else:
            breadcrumb_url = self._breadcrumb_url()

        return BreadcrumbItem(
            title=self.title(),
            url=breadcrumb_url,
        )

    def _breadcrumb_url(self) -> str:
        """Override this method to implement a custom breadcrumb URL

        This can be useful when a mode needs some more contextual information
        to link to the correct page.
        """
        return html.makeuri_contextless([("mode", self.name())], filename="wato.py")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        """Returns the data structure representing the page menu for this mode"""
        return PageMenu(breadcrumb=breadcrumb)

    def buttons(self) -> None:
        global_buttons()

    def action(self) -> ActionResult:
        pass

    def page(self) -> None:
        html.show_message(_("(This module is not yet implemented)"))

    def handle_page(self) -> None:
        return self.page()
