#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple, Type, Union

import cmk.utils.plugin_registry
import cmk.utils.regex
from cmk.utils.type_defs import TagID

from cmk.gui.config import active_config, builtin_role_ids, register_post_config_load_hook
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.permissions import declare_permission, permission_section_registry, PermissionSection

# Imported for plugins
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.html import HTML


@permission_section_registry.register
class PermissionSectionIconsAndActions(PermissionSection):
    @property
    def name(self):
        return "icons_and_actions"

    @property
    def title(self) -> str:
        return _("Icons")

    @property
    def do_sort(self):
        return True


class Icon(abc.ABC):
    _custom_toplevel: Optional[bool] = None
    _custom_sort_index: Optional[int] = None

    @classmethod
    def type(cls) -> str:
        return "icon"

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def override_toplevel(cls, toplevel: bool) -> None:
        cls._custom_toplevel = toplevel

    @classmethod
    def override_sort_index(cls, sort_index: int) -> None:
        cls._custom_sort_index = sort_index

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def render(
        self,
        what: str,
        row: Row,
        tags: List[TagID],
        custom_vars: Dict[str, str],
    ) -> Union[None, str, HTML, Tuple[str, str], Tuple[str, str, str]]:
        raise NotImplementedError()

    def columns(self) -> List[str]:
        """List of livestatus columns needed by this icon idependent of
        the queried table. The table prefix will be added to each column
        (e.g. name -> host_name)"""
        return []

    def host_columns(self) -> List[str]:
        """List of livestatus columns needed by this icon when it is
        displayed for a host row. The prefix host_ will be added to each
        column (e.g. name -> host_name)"""
        return []

    def service_columns(self) -> List[str]:
        """List of livestatus columns needed by this icon when it is
        displayed for a service row. The prefix host_ will be added to each
        column (e.g. description -> service_description)"""
        return []

    def default_toplevel(self) -> bool:
        """Whether or not to display the icon in the column or the action menu"""
        return False

    def default_sort_index(self) -> int:
        return 30

    def toplevel(self) -> bool:
        if self._custom_toplevel is not None:
            return self._custom_toplevel
        return self.default_toplevel()

    def sort_index(self) -> int:
        if self._custom_sort_index is not None:
            return self._custom_sort_index
        return self.default_sort_index()


class IconRegistry(cmk.utils.plugin_registry.Registry[Type[Icon]]):
    def plugin_name(self, instance):
        return instance.ident()

    def registration_hook(self, instance):
        ident = self.plugin_name(instance)
        declare_permission(
            "icons_and_actions.%s" % ident,
            ident,
            _("Allow to see the icon %s in the host and service views") % ident,
            builtin_role_ids,
        )


icon_and_action_registry = IconRegistry()


def update_icons_from_configuration():
    _update_builtin_icons(active_config.builtin_icon_visibility)
    _register_custom_user_icons_and_actions(active_config.user_icons_and_actions)


register_post_config_load_hook(update_icons_from_configuration)


def _update_builtin_icons(builtin_icon_visibility):
    # Now apply the global settings customized options
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icon_and_action_registry.get(icon_id)
        if icon is None:
            continue

        if "toplevel" in cfg:
            icon.override_toplevel(cfg["toplevel"])
        if "sort_index" in cfg:
            icon.override_sort_index(cfg["sort_index"])


def _register_custom_user_icons_and_actions(user_icons_and_actions):
    for icon_id, icon_cfg in user_icons_and_actions.items():
        icon_class = type(
            "CustomIcon%s" % icon_id.title(),
            (Icon,),
            {
                "_ident": icon_id,
                "_icon_spec": icon_cfg,
                "ident": classmethod(lambda cls: cls._ident),
                "title": classmethod(lambda cls: cls._icon_spec.get("title", cls._ident)),
                "type": classmethod(lambda cls: "custom_icon"),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 15),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: (
                    self._icon_spec["icon"],
                    self._icon_spec.get("title"),
                    self._icon_spec.get("url"),
                ),
            },
        )

        icon_and_action_registry.register(icon_class)


IconObjectType = Literal["host", "service"]


@dataclass
class ABCIconEntry:
    sort_index: int


@dataclass
class LegacyIconEntry(ABCIconEntry):
    code: HTML


@dataclass
class IconEntry(ABCIconEntry):
    icon_name: str
    title: Optional[str] = None
    url_spec: Union[None, Tuple[str, str], str] = None


# .
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

# Use this structure for new icons
# TODO: Move this to cmk.gui.views once this is only used by legacy view/icon plugins
multisite_icons_and_actions: Dict[str, Dict[str, Any]] = {}


def get_multisite_icons() -> Dict[str, Icon]:
    icons = {}

    for icon_class in icon_and_action_registry.values():
        icons[icon_class.ident()] = icon_class()

    return icons


def get_icons(what: IconObjectType, row: Row, toplevel: bool) -> List[ABCIconEntry]:
    host_custom_vars = dict(
        zip(
            row["host_custom_variable_names"],
            row["host_custom_variable_values"],
        )
    )

    if what != "host":
        custom_vars = dict(
            zip(
                row[what + "_custom_variable_names"],
                row[what + "_custom_variable_values"],
            )
        )
    else:
        custom_vars = host_custom_vars

    # Extract needed custom variables
    tags = host_custom_vars.get("TAGS", "").split()
    user_icon_ids = custom_vars.get("ACTIONS", "").split(",")

    return sorted(
        _process_icons(what, row, tags, host_custom_vars, toplevel, user_icon_ids),
        key=lambda i: i.sort_index,
    )


def _process_icons(
    what: IconObjectType,
    row: Row,
    tags: List[TagID],
    custom_vars: Dict[str, str],
    toplevel: bool,
    user_icon_ids: List[str],
) -> List[ABCIconEntry]:
    icons: List[ABCIconEntry] = []
    for icon_id, icon in get_multisite_icons().items():
        if icon.toplevel() != toplevel:
            continue

        if icon.type() == "custom_icon" and icon_id not in user_icon_ids:
            continue

        if not user.may("icons_and_actions.%s" % icon_id):
            continue

        try:
            for result in _process_icon(what, row, tags, custom_vars, icon_id, icon):
                icons.append(result)
        except Exception:
            icons.append(
                IconEntry(
                    sort_index=icon.sort_index(),
                    icon_name="alert",
                    title=_("Exception in icon '%s': %s")
                    % (
                        icon_id,
                        traceback.format_exc(),
                    ),
                )
            )
    return icons


def _process_icon(
    what: IconObjectType,
    row: Row,
    tags: List[TagID],
    custom_vars: Dict[str, str],
    icon_id: str,
    icon: Icon,
) -> Iterator[ABCIconEntry]:
    # In old versions, the icons produced html code directly. The new API
    # is that the icon functions need to return:
    # a) None          - nothing to be rendered
    # b) single string - the icon name (without .png)
    # c) tuple         - icon, title
    # d) triple        - icon, title, url
    result: Union[None, str, HTML, Tuple[str, str], Tuple[str, str, str]]
    try:
        result = icon.render(what, row, tags, custom_vars)
    except Exception:
        if active_config.debug:
            raise
        yield IconEntry(
            sort_index=icon.sort_index(),
            icon_name="alert",
            title=_("Exception in icon '%s': %s") % (icon_id, traceback.format_exc()),
        )

    if result is None:
        return

    title, url = None, None
    icon_name: str = ""
    if isinstance(result, (str, HTML)):
        # TODO: This is handling the deprecated API with 1.2.7. Remove this one day. But there
        # are icons that still use this API. These need to be cleaned up before.
        # LM: There are icons that still use this API
        if (isinstance(result, str) and result[0] == "<") or (
            isinstance(result, HTML) and str(result)[0] == "<"
        ):
            # seems like an old format icon (html code). In regular rendering
            # case (html), it can simply be appended to the output. Otherwise
            # extract the icon name from icon images
            if html.output_format == "html":
                if isinstance(result, str):
                    result = escape_to_html(result)
                yield LegacyIconEntry(sort_index=icon.sort_index(), code=result)
            else:
                # Strip icon names out of HTML code that is generated by htmllib.render_icon()
                for n in cmk.utils.regex.regex('<img src="([^"]*)"[^>]*>').findall(str(result)):
                    if n.startswith("images/"):
                        n = n[7:]
                    if n.startswith("icon_"):
                        n = n[5:]
                    if n.endswith(".png"):
                        n = n[:-4]
                    yield IconEntry(sort_index=icon.sort_index(), icon_name=n)
            return

        assert isinstance(result, str)
        icon_name = result
    else:
        # Mypy does not understand the length checking here. Can not easily be fixed, because we
        # would have to change all the icon plugins.
        if len(result) == 2:
            icon_name, title = result  # type: ignore[misc]
        elif len(result) == 3:
            icon_name, title, url = result  # type: ignore[misc]
        else:
            raise NotImplementedError()

    yield IconEntry(
        sort_index=icon.sort_index(),
        icon_name=icon_name,
        title=title,
        url_spec=url,
    )


def iconpainter_columns(what: IconObjectType, toplevel: Optional[bool]) -> List[ColumnName]:
    cols = {
        "site",
        "host_name",
        "host_address",
        "host_custom_variable_names",
        "host_custom_variable_values",
    }

    if what == "service":
        cols.update(
            [
                "service_description",
                "service_custom_variable_names",
                "service_custom_variable_values",
            ]
        )

    for icon in get_multisite_icons().values():
        if toplevel is None or toplevel == icon.toplevel():
            cols.update([what + "_" + c for c in icon.columns()])
            cols.update(["host_" + c for c in icon.host_columns()])
            if what == "service":
                cols.update(["service_" + c for c in icon.service_columns()])

    return list(cols)
