#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from starlette.status import HTTP_409_CONFLICT

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay


def test_two_relays_cannot_have_the_same_id(
    relay_proxy: RelayProxy,
) -> None:
    """
    Test CT-3. Description:

    POST /relays/{relay_id}
    POST /relays/{relay_id} -> 409 Conflict
    """

    relay_id = str(uuid.uuid4())
    register_relay(relay_id, relay_proxy)
    register_relay(relay_id, relay_proxy, expected_status_code=HTTP_409_CONFLICT)
