#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import traceback
from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.debug import enabled as debug_enabled

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils import add_failed_plugin
from cmk.gui.utils.rule_specs.loader import load_api_v1_rule_specs, LoadedRuleSpec
from cmk.gui.watolib.rulespecs import rulespec_registry


def register() -> None:
    # This is only a placeholder to call to ensure that the module is loaded and recognized as a
    # main module
    pass


def load_plugins() -> None:
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

    register_plugins(loaded_rule_specs)


def register_plugins(loaded_rule_specs: Sequence[LoadedRuleSpec]) -> None:
    for loaded_rule_spec in loaded_rule_specs:
        try:
            from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_rulespec

            legacy_rulespec = convert_to_legacy_rulespec(
                loaded_rule_spec.rule_spec, loaded_rule_spec.edition_only, _
            )
            if legacy_rulespec.name in rulespec_registry.keys():
                logger.debug(
                    "Duplicate rule_spec '%s', keeping legacy rulespec", legacy_rulespec.name
                )
                continue

            rulespec_registry.register(legacy_rulespec)
        except Exception as e:
            if debug_enabled():
                raise e
            logger.error(
                "Error converting to legacy rulespec '%s' : %s", loaded_rule_spec.rule_spec.name, e
            )
            add_failed_plugin(
                Path(traceback.extract_tb(e.__traceback__)[-1].filename),
                Path(__file__).stem,
                loaded_rule_spec.rule_spec.name,
                e,
            )
