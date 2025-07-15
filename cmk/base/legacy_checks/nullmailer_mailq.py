#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.nullmailer_mailq import (
    check_nullmailer_mailq,
    NULLMAILER_MAILQ_DEFAULT_LEVELS,
    parse_nullmailer_mailq,
)

check_info = {}

# Example agent output:
# old format
# <<<nullmailer_mailq>>>
# 8 1

# new format
# <<<nullmailer_mailq>>>
# 8 1 deferred
# 8 1 failed


def discover_nullmailer_mailq(parsed):
    if parsed:
        yield None, {}


check_info["nullmailer_mailq"] = LegacyCheckDefinition(
    name="nullmailer_mailq",
    parse_function=parse_nullmailer_mailq,
    service_name="Nullmailer Queue",
    discovery_function=discover_nullmailer_mailq,
    check_function=check_nullmailer_mailq,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters=NULLMAILER_MAILQ_DEFAULT_LEVELS,
)
