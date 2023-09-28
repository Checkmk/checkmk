#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple


class RelayState(NamedTuple):
    """SAML2 HTTP parameter"""

    target_url: str
    connection_id: str

    def __str__(self) -> str:
        return f"{self.connection_id},{self.target_url}"
