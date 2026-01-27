#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""FormSpecs that allow a selection form preconfigured resources in a setup"""

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.rulesets.v1.form_specs._base import FormSpec


class InternalProxySchema(enum.StrEnum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS4A = "socks4a"
    SOCKS5 = "socks5"
    SOCKS5H = "socks5h"


@dataclass(frozen=True, kw_only=True)
class InternalProxy(
    FormSpec[
        tuple[
            Literal["cmk_postprocessed"],
            Literal["environment_proxy", "no_proxy", "stored_proxy"],
            str,
        ]
        | tuple[
            Literal["cmk_postprocessed"],
            Literal["explicit_proxy"],
            Mapping[str, object],
        ]
    ]
):
    """Specifies a form for configuring a proxy

    Args:
        allowed_schemas: Set of available proxy schemas that can be used in a proxy url
    """

    allowed_schemas: frozenset[InternalProxySchema] = frozenset(InternalProxySchema)


@dataclass(frozen=True, kw_only=True)
class OAuth2Connection(
    FormSpec[
        tuple[
            Literal["cmk_postprocessed"],
            Literal["oauth2_connection"],
            str,
        ]
    ]
):
    """Specifies a form for configuring an OAuth2 connection"""

    connector_type: Literal["microsoft_entra_id"]
