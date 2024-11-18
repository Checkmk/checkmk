#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import Callable, Generator

from pydantic import TypeAdapter, ValidationError

from cmk.utils import tty
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
from cmk.gui.watolib.utils import wato_root_dir

from cmk.update_config.registry import update_action_registry, UpdateAction


class LABELS:
    failed = f"{tty.red}Failed{tty.normal}"
    passed = f"{tty.green}Passed{tty.normal}"


class ValidateConfigFiles(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        """
        1. Validate the data in all registered mk config files.
        2. Validate timeperiods
        3. Validate rules of rulesets in folders
        """

        failures: bool = False
        counter = 1
        for relative_file_path in config_file_registry:
            result, has_failure = _run_and_evaluate_validation(
                relative_file_path,
                counter,
                config_file_registry[relative_file_path].read_file_and_validate,
            )
            failures |= has_failure
            counter += 1
            logger.info(result)

        # Validate timeperiods.mk
        result, has_failure = _run_and_evaluate_validation(
            str(Path(wato_root_dir()) / "timeperiods.mk"),
            counter,
            lambda: validate_timeperiods(load_timeperiods()),
        )
        failures |= has_failure
        counter += 1
        logger.info(result)

        # Validate rulesets in folders
        rule_validator = TypeAdapter(RuleSpec)  # nosemgrep: type-adapter-detected
        for folder_path, validate_result, has_failure in _validate_folder_ruleset_rules(
            folder_tree().root_folder(), rule_validator
        ):
            logger.info(
                _file_format(f"{folder_path}/rules.mk", row_number=counter) + validate_result
            )
            failures |= has_failure
            counter += 1

        if failures:
            logger.info(
                "    We found an issue with the configuration of your site.\n"
                "    Currently it is just a warning to make you aware of the potential problem.\n"
                "    For now you can proceed with the update of your site.\n\n"
                "    However, in the future we will treat this as an error and stop the update procedure.\n"
                "    Because of this, it is important that you make us aware of the issue.\n"
                "    Please send us a support ticket with the information provided here so that we can work\n"
                "    out whether there is migration code missing or the validation needs to be improved.\n\n"
            )


def _file_format(file_path: str, row_number: int) -> str:
    return f"    {tty.yellow}{row_number:02d}{tty.normal} {file_path:.<60} "


def _run_and_evaluate_validation(
    file_path: str, counter: int, validation_call: Callable[[], None]
) -> tuple[str, bool]:
    evaluation_message = _file_format(file_path, counter)
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
    validator = TypeAdapter(TimeperiodSpecs)  # nosemgrep: type-adapter-detected
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

    yield folder.path(), evaluation_message, has_failure

    for sub_folder in folder.subfolders():
        yield from _validate_folder_ruleset_rules(sub_folder, rule_validator)


update_action_registry.register(
    ValidateConfigFiles(
        name="validate_config_files",
        title="Validating configuration files",
        sort_index=998,  # Should be run after any mk file modifications.
        continue_on_failure=True,
    )
)
