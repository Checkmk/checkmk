#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Sequence

from cmk.utils import paths

from cmk.checkengine.checkresults import (  # pylint: disable=cmk-module-layer-violation
    ActiveCheckResult,
)

from cmk.base import check_api  # pylint: disable=cmk-module-layer-violation
from cmk.base.config import load_all_plugins  # pylint: disable=cmk-module-layer-violation


class ValidationStep(enum.Enum):
    AGENT_BASED_PLUGINS = "agent based plugins loading"


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
