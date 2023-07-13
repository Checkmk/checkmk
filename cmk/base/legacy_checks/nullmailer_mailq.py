#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.nullmailer_mailq import (
    check_nullmailer_mailq,
    NULLMAILER_MAILQ_DEFAULT_LEVELS,
    parse_nullmailer_mailq,
)
from cmk.base.config import check_info

# Example agent output:
# old format
# <<<nullmailer_mailq>>>
# 8 1

# new format
# <<<nullmailer_mailq>>>
# 8 1 deferred
# 8 1 failed


def inventory_nullmailer_mailq(parsed):
    if parsed:
        yield "", {}


check_info["nullmailer_mailq"] = LegacyCheckDefinition(
    parse_function=parse_nullmailer_mailq,
    service_name="Nullmailer Queue %s",
    discovery_function=inventory_nullmailer_mailq,
    check_function=check_nullmailer_mailq,
    check_ruleset_name="mail_queue_length",
    check_default_parameters=NULLMAILER_MAILQ_DEFAULT_LEVELS,
)
