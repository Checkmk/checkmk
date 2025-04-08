#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import LoadedConfigFragment

EMPTYCONFIG = LoadedConfigFragment(
    discovery_rules={},
    checkgroup_parameters={},
    service_rule_groups=set(),
    service_descriptions={},
    service_description_translation=(),
    use_new_descriptions_for=(),
    nagios_illegal_chars="",
    cmc_illegal_chars="",
)
