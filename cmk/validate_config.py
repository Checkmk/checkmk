#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from cmk.ccc import tty

from cmk.utils import paths
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.timeperiod import (
    TimeperiodSpecs,
    validate_day_time_ranges,
    validate_timeperiod_exceptions,
)

from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import FolderRulesets, InvalidRuleException
from cmk.gui.watolib.simple_config_file import config_file_registry
from cmk.gui.watolib.timeperiods import load_timeperiods


class LABELS:
    failed = f"{tty.red}Failed{tty.normal}"
    passed = f"{tty.green}Passed{tty.normal}"


@dataclass
class ValidationResult:
    logs_valid: list[str]
    logs_invalid: list[str]


def validate_mk_files() -> ValidationResult:
    """
    NOTE: This function needs to be called within an application context.

    1. Validate the data in all registered mk config files.
    2. Validate timeperiods
    3. Validate rules of rulesets in folders
    """
    logs_invalid: list[str] = []
    logs_valid: list[str] = []
    for relative_file_path in config_file_registry:
        result, has_failure = _run_and_evaluate_validation(
            relative_file_path,
            config_file_registry[relative_file_path].read_file_and_validate,
        )
        if has_failure:
            logs_invalid.append(result)
        else:
            logs_valid.append(result)

    # Validate timeperiods.mk
    result, has_failure = _run_and_evaluate_validation(
        "etc/check_mk/conf.d/wato/timeperiods.mk",
        lambda: validate_timeperiods(load_timeperiods()),
    )
    if has_failure:
        logs_invalid.append(result)
    else:
        logs_valid.append(result)

    # Validate rulesets in folders
    # No performance impact - only called during cmk-update-config
    rule_validator = TypeAdapter(RuleSpec)  # nosemgrep: type-adapter-detected
    for folder_path, validate_result, has_failure in _validate_folder_ruleset_rules(
        folder_tree().root_folder(), rule_validator
    ):
        message = _file_format(f"{folder_path}/rules.mk") + validate_result
        if has_failure:
            logs_invalid.append(message)
        else:
            logs_valid.append(message)

    return ValidationResult(logs_valid=logs_valid, logs_invalid=logs_invalid)


def _file_format(file_path: str) -> str:
    return f"{file_path:.<60} "


def _run_and_evaluate_validation(
    file_path: str, validation_call: Callable[[], None]
) -> tuple[str, bool]:
    evaluation_message = _file_format(file_path)
    has_failure = False
    try:
        validation_call()
    except (NotImplementedError, ConfigValidationError, ValueError, Exception) as exc:
        evaluation_message += f"{LABELS.failed}\n\t{str(exc)}"
        has_failure = True
    else:
        evaluation_message += LABELS.passed
    return evaluation_message, has_failure


def validate_timeperiods(time_periods: TimeperiodSpecs) -> None:
    # No performance impact - only called during cmk-update-config
    validator = TypeAdapter[TimeperiodSpecs](TimeperiodSpecs)  # nosemgrep: type-adapter-detected
    validator.validate_python(time_periods, strict=True)

    invalid_timeperiods = []
    for _name, timeperiod in time_periods.items():
        try:
            validate_day_time_ranges(timeperiod)
            validate_timeperiod_exceptions(timeperiod)
        except ValueError as exc:
            invalid_timeperiods.append(f"{_name}: {str(exc)}")

    if invalid_timeperiods:
        raise ValueError(f"Invalid timeperiods:\n\t{invalid_timeperiods}")


def _validate_folder_ruleset_rules(
    folder: Folder, rule_validator: TypeAdapter
) -> Generator[tuple[str, str, bool], None, None]:
    """Validate the rulesets of each folder recursively

    Folders are allowed to have overlapping names so display the folder path
    """
    try:  # the validation already starts during loading of the rulesets & underlying rules
        for ruleset in FolderRulesets.load_folder_rulesets(folder).get_rulesets().values():
            for rules in ruleset.rules.values():
                for rule in rules:
                    rule_validator.validate_python(rule.to_config(), strict=True)
    except (InvalidRuleException, ValidationError, Exception) as e:
        evaluation_message = f"{LABELS.failed}\n\t{str(e)}"
        has_failure = True
    else:
        evaluation_message = LABELS.passed
        has_failure = False

    yield (
        str(Path(folder.filesystem_path()).relative_to(paths.omd_root)),
        evaluation_message,
        has_failure,
    )

    for sub_folder in folder.subfolders():
        yield from _validate_folder_ruleset_rules(sub_folder, rule_validator)
