#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.maps.rest_api.models.map import MapConfig
from cmk.maps.rest_api.models.response_models import MapVisibility


@api_model
class MapRequest:
    """Create/update body: the full map payload plus its sharing scope.

    On update the map name comes from the path; ``config.name`` must match it.
    ``visibility`` is clamped server-side to what the user may actually publish.
    """

    config: MapConfig = api_field(description="The full map configuration to store.")
    visibility: MapVisibility | ApiOmitted = api_field(
        description="Sharing scope; omitted stays private on create / unchanged on update.",
        default_factory=ApiOmitted,
    )
