#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

from livestatus import SiteId

from cmk.gui.type_defs import UserSpec


def user_associated_sites(user_attrs: UserSpec) -> Sequence[SiteId] | None:
    return user_attrs.get("authorized_sites")
