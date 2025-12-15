#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import UUID

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class RegisterHost:
    uuid: UUID = api_field(
        description="A valid UUID.",
        example="34e4c967-1591-4883-8cdf-0e335b09618d",
    )
