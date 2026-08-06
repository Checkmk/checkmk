#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _


def validate_id(
    mode: str,
    existing_entries: Mapping[str, object],
    reserved_unique_ids: list[str] | None = None,
) -> Callable[[Mapping[str, object], str], None]:
    """Validate ID of newly created or cloned pagetype or visual"""

    def _validate(properties: Mapping[str, object], varprefix: str) -> None:
        name = str(properties["name"])
        if mode in ["create", "clone"]:
            if existing_entries.get(name):
                raise MKUserError(
                    varprefix + "_p_name",
                    _("You already have an element with the ID <b>%(name)s</b>") % {"name": name},
                )
            if reserved_unique_ids is not None and name in reserved_unique_ids:
                raise MKUserError(
                    varprefix + "_p_name",
                    _("ID <b>%(name)s</b> is reserved for internal use.") % {"name": name},
                )

    return _validate
