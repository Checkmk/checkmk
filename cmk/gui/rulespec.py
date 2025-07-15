#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.debug import enabled as debug_enabled

from cmk.gui.log import logger
from cmk.gui.utils import add_failed_plugin
from cmk.gui.utils.rule_specs.loader import load_api_v1_rule_specs, LoadedRuleSpec
from cmk.gui.utils.rule_specs.registering import register_plugin
from cmk.gui.watolib.notification_parameter import NotificationParameterRegistry
from cmk.gui.watolib.rulespecs import RulespecRegistry

from cmk.rulesets.v1.rule_specs import NotificationParameters


def register(
    rulespec_registry: RulespecRegistry,
    notification_parameter_registry: NotificationParameterRegistry,
) -> None:
    errors, loaded_rule_specs = load_api_v1_rule_specs(debug_enabled())
    if errors:
        logger.error("Error loading rulespecs: %s", errors)
        for error in errors:
            module_path = str(error).split(":", maxsplit=1)[0]
            add_failed_plugin(
                Path(module_path.replace(".", "/") + ".py"),
                Path(__file__).stem,
                module_path.split(".")[-1],
                error,
            )

    register_plugins(rulespec_registry, notification_parameter_registry, loaded_rule_specs)


def register_plugins(
    rulespec_registry: RulespecRegistry,
    notification_parameter_registry: NotificationParameterRegistry,
    loaded_rule_specs: Sequence[LoadedRuleSpec],
) -> None:
    for loaded_rule_spec in loaded_rule_specs:
        if isinstance(loaded_rule_spec.rule_spec, NotificationParameters):
            notification_parameter_registry.register(loaded_rule_spec.rule_spec)

        register_plugin(rulespec_registry, loaded_rule_spec)
