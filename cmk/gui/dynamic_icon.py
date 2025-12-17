#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

from cmk.gui.theme import Theme
from cmk.gui.type_defs import DynamicIcon
from cmk.shared_typing import icon as st

# All functions in that file are about icons that the user can change.
# Dashboards and Views have such icons.
# don't use this if you handle icons that are known at build time!


def resolve_icon_name(icon: DynamicIcon, theme: Theme) -> st.DynamicIcon:
    if isinstance(icon, dict):
        icon_name = icon["icon"]
        emblem_name = icon["emblem"]
    else:
        icon_name = icon
        emblem_name = None

    icon_result: st.DefaultIcon | st.UserIcon

    if icon_name.startswith("themes/"):
        if Path(icon_name).name.startswith("emblem"):
            # this is a hack for being able to show emblem icons in the valuespec icon selector
            icon_id = Path(icon_name).stem
            icon_result = st.UserIcon(id=icon_id, path=str(icon_name))
        else:
            raise RuntimeError("only emblem icons are allowed to use paths as icon name.")
    else:
        icon_resolved = theme.detect_icon_path(icon_name, "icon_")

        if icon_resolved.startswith("themes/"):
            icon_result = st.DefaultIcon(id=icon_name.replace("_", "-"))
        elif icon_resolved.startswith("images/"):
            icon_result = st.UserIcon(id=icon_name, path=icon_resolved)
        else:
            return st.DefaultIcon(id="missing")

    if emblem_name:
        # we don't have to solve the emblem name in any special way,
        # as they can not be configured by the user
        return st.EmblemIcon(icon=icon_result, emblem=emblem_name)

    return icon_result
