#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import IgnoreResultsError


def is_ibm_mq_service_vanished(item: str, parsed: Mapping[str, Any]) -> bool:
    """
    Returns true if queue or channel is not contained anymore in the agent
    output but queue manager is known as RUNNING. Throws MKCounterWrapped to
    mark service as STALE if QMGR is not RUNNING.
    """
    if item in parsed:
        return False

    qmgr_name = item.split(":", 1)[0]
    qmgr_status = "RUNNING"
    if qmgr_name in parsed:
        qmgr_status = parsed[qmgr_name]["STATUS"]

    if qmgr_status == "RUNNING":
        return True
    raise IgnoreResultsError("Stale because queue manager %s" % qmgr_status)
