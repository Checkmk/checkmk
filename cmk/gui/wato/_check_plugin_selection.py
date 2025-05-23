#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, DualListChoice, Transform
from cmk.gui.watolib.check_mk_automations import get_check_information_cached


def CheckPluginSelection(
    *,
    title: str,
    help_: str,
) -> Transform:
    return Transform(
        valuespec=Dictionary(
            title=title,
            help=help_,
            elements=[
                ("host", _CheckTypeHostSelection(title=_("Checks on regular hosts"))),
                ("mgmt", _CheckTypeMgmtSelection(title=_("Checks on management boards"))),
            ],
            optional_keys=["mgmt"],
        ),
        # omit empty mgmt key
        to_valuespec=lambda list_: {
            k: v
            for k, v in (
                ("host", [name for name in list_ if not name.startswith("mgmt_")]),
                ("mgmt", [name[5:] for name in list_ if name.startswith("mgmt_")]),
            )
            if v or k == "host"
        },
        from_valuespec=lambda dict_: dict_["host"] + [f"mgmt_{n}" for n in dict_.get("mgmt", ())],
    )


class _CheckTypeHostSelection(DualListChoice):
    def __init__(self, title: str) -> None:
        super().__init__(rows=25, title=title)

    def get_elements(self):
        checks = get_check_information_cached(debug=active_config.debug)
        return [
            (str(cn), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
            # filter out plug-ins implemented *explicitly* for management boards
            if not cn.is_management_name()
        ]


class _CheckTypeMgmtSelection(DualListChoice):
    def __init__(self, title: str) -> None:
        super().__init__(rows=25, title=title)

    def get_elements(self):
        checks = get_check_information_cached(debug=active_config.debug)
        return [
            (str(cn.create_basic_name()), (str(cn) + " - " + c["title"])[:60])
            for (cn, c) in checks.items()
        ]
