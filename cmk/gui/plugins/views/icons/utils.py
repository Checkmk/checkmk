#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Text, List, Optional, Tuple, TYPE_CHECKING, Union  # pylint: disable=unused-import
import six

import cmk.gui.config as config
from cmk.gui.i18n import _
import cmk.utils.plugin_registry
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    declare_permission,
)

if TYPE_CHECKING:
    from cmk.gui.htmllib import HTML  # pylint: disable=unused-import


@permission_section_registry.register
class PermissionSectionIconsAndActions(PermissionSection):
    @property
    def name(self):
        return "icons_and_actions"

    @property
    def title(self):
        return _("Icons")

    @property
    def do_sort(self):
        return True


class Icon(six.with_metaclass(abc.ABCMeta, object)):
    _custom_toplevel = None  # type: Optional[bool]
    _custom_sort_index = None  # type: Optional[int]

    @classmethod
    def type(cls):
        # type: () -> str
        return "icon"

    @classmethod
    def override_toplevel(cls, toplevel):
        # type: (bool) -> None
        cls._custom_toplevel = toplevel

    @classmethod
    def override_sort_index(cls, sort_index):
        # type: (int) -> None
        cls._custom_sort_index = sort_index

    @classmethod
    @abc.abstractmethod
    def ident(cls):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractmethod
    def render(self, what, row, tags, custom_vars):
        # type: (str, dict, list, dict) -> Optional[Union[HTML, Tuple, str, Text]]
        raise NotImplementedError()

    def columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon idependent of
        the queried table. The table prefix will be added to each column
        (e.g. name -> host_name)"""
        return []

    def host_columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon when it is
        displayed for a host row. The prefix host_ will be added to each
        column (e.g. name -> host_name)"""
        return []

    def service_columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon when it is
        displayed for a service row. The prefix host_ will be added to each
        column (e.g. description -> service_description)"""
        return []

    def default_toplevel(self):
        # type: () -> bool
        """Whether or not to display the icon in the column or the action menu"""
        return False

    def default_sort_index(self):
        # type: () -> int
        return 30

    def toplevel(self):
        # type: () -> bool
        if self._custom_toplevel is not None:
            return self._custom_toplevel
        return self.default_toplevel()

    def sort_index(self):
        # type: () -> int
        if self._custom_sort_index is not None:
            return self._custom_sort_index
        return self.default_sort_index()


class IconRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return Icon

    def plugin_name(self, plugin_class):
        return plugin_class.ident()

    def registration_hook(self, plugin_class):
        ident = self.plugin_name(plugin_class)
        declare_permission("icons_and_actions.%s" % ident, ident,
                           _("Allow to see the icon %s in the host and service views") % ident,
                           config.builtin_role_ids)


icon_and_action_registry = IconRegistry()


def update_icons_from_configuration():
    _update_builtin_icons(config.builtin_icon_visibility)
    _register_custom_user_icons_and_actions(config.user_icons_and_actions)


config.register_post_config_load_hook(update_icons_from_configuration)


def _update_builtin_icons(builtin_icon_visibility):
    # Now apply the global settings customized options
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icon_and_action_registry.get(icon_id)
        if icon is None:
            continue

        if 'toplevel' in cfg:
            icon.override_toplevel(cfg['toplevel'])
        if 'sort_index' in cfg:
            icon.override_sort_index(cfg['sort_index'])


def _register_custom_user_icons_and_actions(user_icons_and_actions):
    for icon_id, icon_cfg in user_icons_and_actions.items():
        icon_class = type(
            "CustomIcon%s" % icon_id.title(), (Icon,), {
                "_ident": icon_id,
                "_icon_spec": icon_cfg,
                "ident": classmethod(lambda cls: cls._ident),
                "type": classmethod(lambda cls: "custom_icon"),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 15),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args:
                          (self._icon_spec["icon"], self._icon_spec.get("title"),
                           self._icon_spec.get("url")),
            })

        icon_and_action_registry.register(icon_class)
