#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Script to validate if all available plugins can be loaded"""

import enum
import os
import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from cmk.utils import debug, paths

from cmk.checkengine.checkresults import (  # pylint: disable=cmk-module-layer-violation
    ActiveCheckResult,
)

from cmk.base import check_api  # pylint: disable=cmk-module-layer-violation
from cmk.base.config import load_all_plugins  # pylint: disable=cmk-module-layer-violation

from cmk.gui.main_modules import load_plugins  # pylint: disable=cmk-module-layer-violation
from cmk.gui.utils import get_failed_plugins  # pylint: disable=cmk-module-layer-violation
from cmk.gui.utils.script_helpers import gui_context  # pylint: disable=cmk-module-layer-violation
from cmk.gui.watolib.rulespecs import (  # pylint: disable=cmk-module-layer-violation
    rulespec_registry,
)


class ValidationStep(enum.Enum):
    AGENT_BASED_PLUGINS = "agent based plugins loading"
    RULE_SPECS = "rule specs loading"
    RULE_SPEC_FORMS = "rule specs forms creation"


def to_result(step: ValidationStep, errors: Sequence[str]) -> ActiveCheckResult:
    return ActiveCheckResult(
        state=2 if errors else 0,
        summary=f"{step.value.capitalize()} failed"
        if errors
        else f"{step.value.capitalize()} succeeded",
        details=list(errors),
    )


def _validate_agent_based_plugin_loading() -> ActiveCheckResult:
    errors = load_all_plugins(
        check_api.get_check_api_context,
        local_checks_dir=paths.local_checks_dir,
        checks_dir=paths.checks_dir,
    )

    return to_result(ValidationStep.AGENT_BASED_PLUGINS, errors)


def _validate_rule_spec_loading() -> ActiveCheckResult:
    load_plugins()
    errors = [
        f"Error in rule spec {module_name}: {exc}"
        for path, subcomponent, module_name, exc in get_failed_plugins()
    ]
    return to_result(ValidationStep.RULE_SPECS, errors)


def _validate_rule_spec_form_creation() -> ActiveCheckResult:
    if not os.environ.get("OMD_SITE"):
        return ActiveCheckResult(
            state=1,
            summary=f"{ValidationStep.RULE_SPEC_FORMS.value.capitalize()} skipped",
            details=["Form creation validation can only be used as site user"],
        )

    errors = []
    with gui_context():
        for loaded_rule_spec in rulespec_registry.values():
            try:
                _ = loaded_rule_spec.valuespec
            except Exception as e:
                if debug.enabled():
                    raise e
                errors.append(f"{type(loaded_rule_spec).__name__} '{loaded_rule_spec.name}': {e}")

    return to_result(ValidationStep.RULE_SPEC_FORMS, errors)


def validate_plugins() -> ActiveCheckResult:
    sub_results = [
        _validate_agent_based_plugin_loading(),
        _validate_rule_spec_loading(),
        _validate_rule_spec_form_creation(),
    ]
    return ActiveCheckResult.from_subresults(*sub_results)


def main() -> int:
    parser = ArgumentParser(prog="cmk-validate-plugins", description=__doc__)
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode (raise Exceptions instead of logging them)",
    )
    args = parser.parse_args()

    if args.debug:
        debug.enable()

    validation_result = validate_plugins()

    sys.stdout.write(validation_result.as_text())
    return validation_result.state
