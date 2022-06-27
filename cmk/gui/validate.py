#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _


def validate_id(
    mode: str,
    existing_entries: Dict[str, Any],
    reserved_unique_ids: Optional[list[str]] = None,
) -> Callable[[Dict[str, Any], str], None]:
    """Validate ID of newly created or cloned pagetype or visual"""

    def _validate(properties: Dict[str, Any], varprefix: str) -> None:
        name = properties["name"]
        if mode in ["create", "clone"]:
            if existing_entries.get(name):
                raise MKUserError(
                    varprefix + "_p_name",
                    _("You already have an element with the ID <b>%s</b>") % name,
                )
            if reserved_unique_ids is not None and name in reserved_unique_ids:
                raise MKUserError(
                    varprefix + "_p_name",
                    _("ID <b>%s</b> is reserved for internal use.") % name,
                )

    return _validate
