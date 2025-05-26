#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import cmk.utils.paths

from cmk.gui.openapi.restful_objects.type_defs import EndpointTarget

LIVESTATUS_GENERIC_EXPLANATION = (
    "The REST API exclusively manages the preparation and dispatch of commands to Livestatus. "
    "These commands are processed in an asynchronous manner, and the REST API does not validate "
    "the successful execution of commands on Livestatus. To investigate any failures in Livestatus, "
    "one should refer to the corresponding log. Also you can refer to [Queries through the REST API](#section/Queries-through-the-REST-API) "
    "section for further information."
)


def spec_path(target: EndpointTarget) -> Path:
    return cmk.utils.paths.var_dir / "rest_api" / "spec" / f"{target}.spec"
