#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Literal

from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import Permission
from cmk.gui.type_defs import BuiltinIconVisibility, IconSpec, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.ruleset_matcher.tags import TagID
from cmk.web.utils.icons import DynamicIcon, StaticIcon

from .base import Icon, IconConfig
from .permission_section import PERMISSION_SECTION_ICONS_AND_ACTIONS


def update_builtin_icons_from_config(
    icons: dict[str, Icon], builtin_icon_visibility: dict[str, BuiltinIconVisibility]
) -> dict[str, Icon]:
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icons.get(icon_id)
        if icon is None:
            continue

        icon.override_toplevel(cfg.get("toplevel"))
        icon.override_sort_index(cfg.get("sort_index"))

    return icons


def config_based_icons(user_icons_and_actions: dict[str, IconSpec]) -> dict[str, Icon]:
    return {
        icon_id: Icon(
            ident=icon_id,
            title=icon_spec.get("title", icon_id),
            columns=[],
            host_columns=[],
            service_columns=[],
            render=_make_render_function(icon_spec=icon_spec),
            type_="custom_icon",
            sort_index=icon_spec.get("sort_index", 15),
            toplevel=icon_spec.get("toplevel", False),
        )
        for icon_id, icon_spec in user_icons_and_actions.items()
    }


def _make_render_function(
    icon_spec: IconSpec,
) -> Callable[
    [
        Literal["host", "service"],
        Row,
        Sequence[TagID],
        Mapping[str, str],
        UserPermissions,
        IconConfig,
    ],
    tuple[StaticIcon | DynamicIcon, str | None, tuple[str, str] | None],
]:
    def _render(
        _what: Literal["host", "service"],
        _row: Row,
        _tags: Sequence[TagID],
        _custom_vars: Mapping[str, str],
        _user_permissions: UserPermissions,
        _icon_cfg: IconConfig,
    ) -> tuple[StaticIcon | DynamicIcon, str | None, tuple[str, str] | None]:
        return (
            icon_spec["icon"],
            icon_spec.get("title"),
            icon_spec.get("url"),
        )

    return _render


def icons_and_actions_permissions(icons: Mapping[str, IconSpec]) -> Iterator[Permission]:
    for ident in icons:
        yield Permission(
            section=PERMISSION_SECTION_ICONS_AND_ACTIONS,
            name=ident,
            title=ident,
            description=_("Allow to see the icon %(ident)s in the host and service views")
            % {"ident": ident},
            defaults=default_authorized_builtin_role_ids,
        )
