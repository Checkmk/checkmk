#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.utils.debug import enabled as debug_enabled

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.rulespecs.legacy_converter import convert_to_legacy_rulespec
from cmk.gui.utils.rulespecs.loader import load_api_v1_rulespecs, RuleSpec
from cmk.gui.watolib.rulespecs import rulespec_registry


def load_plugins() -> None:
    errors, loaded_rulespecs = load_api_v1_rulespecs(debug_enabled())
    if errors:
        logger.error("Error loading rulespecs: %s", errors)

    register_plugins(loaded_rulespecs)


def register_plugins(loaded_rulespecs: Mapping[str, RuleSpec]) -> None:
    for name, rulespec in loaded_rulespecs.items():
        try:
            legacy_rulespec = convert_to_legacy_rulespec(rulespec, _)
            if legacy_rulespec.name in rulespec_registry.keys():
                logger.debug(
                    "Duplicate rulespec '%s', keeping legacy rulespec", legacy_rulespec.name
                )
                continue
            rulespec_registry.register(legacy_rulespec)
        except Exception as e:
            logger.error("Error converting to legacy rulespec '%s' : %s", name, e)
