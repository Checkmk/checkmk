#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils.oauth2_connection import OAuth2ConnectorType


@dataclass(frozen=True, kw_only=True)
class OAuth2ConnectionSetup(FormSpec[dict[str, str]]):
    connector_type: OAuth2ConnectorType
