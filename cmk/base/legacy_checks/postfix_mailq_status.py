#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# single
# <<<postfix_mailq_status:sep(58)>>>
# postfix/postfix-script: the Postfix mail system is running: PID: 2839
# postfix: Postfix is running with backwards-compatible default settings^M postfix: See http://www.postfix.org/COMPATIBILITY_README.html for details^M postfix: To disable backwards compatibility use "postconf compatibility_level=2" and "postfix reload"^M postfix/postfix-script: the Postfix mail system is running: PID: 3096

# multi instances
# <<<postfix_mailq_status:sep(58)>>>
# postfix/postfix-script: the Postfix mail system is running: PID: 12910
# postfix-external/postfix-script: the Postfix mail system is running: PID: 12982
# postfix-internal/postfix-script: the Postfix mail system is running: PID: 13051
# postfix-uat-cdi/postfix-script: the Postfix mail system is not running


# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any, Iterator

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import State
from cmk.base.plugins.agent_based.postfix_mailq_status import PostfixError, PostfixPid


def inventory_postfix_mailq_status(
    section: Mapping[str, PostfixError | PostfixPid]
) -> Iterator[Any]:
    yield from ((queuename, None) for queuename in section)


def check_postfix_mailq_status(
    item: str, params: object, section: Mapping[str, PostfixError | PostfixPid]
) -> Iterator[Any]:
    if not (postfix := section.get(item)):
        return

    if isinstance(postfix, PostfixPid):
        yield State.OK.value, "Status: the Postfix mail system is running"
        yield State.OK.value, f"PID: {postfix}"
    else:
        yield State.CRIT.value, f"Status: {postfix.value}"


check_info["postfix_mailq_status"] = LegacyCheckDefinition(
    service_name="Postfix status %s",
    discovery_function=inventory_postfix_mailq_status,
    check_function=check_postfix_mailq_status,
)
