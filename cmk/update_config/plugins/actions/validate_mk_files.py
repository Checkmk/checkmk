#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Generator
from logging import Logger
from pathlib import Path

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

        etc_wato_path = Path("etc/check_mk/conf.d/wato")
        faulty_configurations: list[str] = []
        for relative_file_path in config_file_registry:
            result, has_failure = _run_and_evaluate_validation(
                relative_file_path,
                config_file_registry[relative_file_path].read_file_and_validate,
            )
            if has_failure:
                faulty_configurations.append(result)

        # Validate timeperiods.mk
        result, has_failure = _run_and_evaluate_validation(
            str(etc_wato_path / "timeperiods.mk"),
            lambda: validate_timeperiods(load_timeperiods()),
        )
        if has_failure:
            faulty_configurations.append(result)

        # Validate rulesets in folders
        rule_validator = TypeAdapter(RuleSpec)  # nosemgrep: type-adapter-detected
        for folder_path, validate_result, has_failure in _validate_folder_ruleset_rules(
            folder_tree().root_folder(), rule_validator
        ):
            if has_failure:
                faulty_configurations.append(
                    _file_format(str(etc_wato_path / f"{folder_path}/rules.mk") + validate_result)
                )

        if faulty_configurations:
            logger.info(
                "\n"
                "       We have identified an issue with the configuration of your site.\n\n"
                "       Currently, this is a warning to make you aware of a potential problem.\n"
                "       Our validation process checks your configuration files against a work-in-progress internal representation.\n"
                "       In this case, we found at least one mismatch between the two.\n\n"
                "       For now you can proceed with the update of your site.\n"
                "       However, in the future we will treat this as an error and stop the update procedure.\n"
                "       To prevent any interruptions, we kindly ask you to notify us about this issue.\n\n"
                "       Please send us a support ticket if you believe there are no issues with your relevant configuration mk files.\n"
                "       Be sure to include the name of the configuration file, the displayed error message and \n"
                "       if possible the mk file itself.\n"
                "       This information will help us investigate further and determine whether improvements are needed.\n\n"
                "       The following mk files had issues during the validation:\n"
            )
            for message in faulty_configurations:
                logger.info(message)


def _file_format(file_path: str) -> str:
    return f"\t{file_path:.<60} "


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
