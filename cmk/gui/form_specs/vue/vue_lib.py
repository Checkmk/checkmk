#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

# Experimental only registry (not an actual registry)
form_spec_registry: dict[str, LoadedRuleSpec] = {}
