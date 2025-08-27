#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.relay_protocols.tasks import TaskType

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay
from .test_lib.tasks import push_task


def test_store_fetching_tasks(relay_proxy: RelayProxy) -> None:
    register_relay("relay_id", relay_proxy)
    push_task(
        relay_proxy=relay_proxy,
        relay_id="relay_id",
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )
