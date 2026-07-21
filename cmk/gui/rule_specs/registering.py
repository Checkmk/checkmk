#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from pathlib import Path

from cmk.ccc.debug import enabled as debug_enabled
from cmk.gui.i18n import _
from cmk.gui.legacy_plugins import add_failed_plugin
from cmk.gui.log import logger
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.gui.rule_specs.loader import LoadedRuleSpec
from cmk.gui.watolib.rulespecs import RulespecRegistry


def register_plugin(rulespec_registry: RulespecRegistry, loaded_rule_spec: LoadedRuleSpec) -> None:
    try:
        legacy_rulespec = convert_to_legacy_rulespec(
            loaded_rule_spec.rule_spec, loaded_rule_spec.edition_only, _
        )
        if legacy_rulespec.name in rulespec_registry:
            logger.debug(
                "Duplicate rule_spec '%(rulespec_name)s', overriding legacy rulespec",
                {"rulespec_name": legacy_rulespec.name},
            )

        rulespec_registry.register(legacy_rulespec)
    except Exception as e:
        if debug_enabled():
            raise e
        logger.error(
            "Error converting to legacy rulespec '%(rulespec_name)s' : %(error)s",
            {"rulespec_name": loaded_rule_spec.rule_spec.name, "error": e},
        )
        add_failed_plugin(
            Path(traceback.extract_tb(e.__traceback__)[-1].filename),
            Path(__file__).stem,
            loaded_rule_spec.rule_spec.name,
            e,
        )
