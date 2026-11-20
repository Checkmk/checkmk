#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import active_config
from cmk.gui.crash_handler import create_gui_crash_report
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.valuespec import ValueSpec
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Ruleset, RulesetCollection
from cmk.gui.watolib.rulespecs import FormSpecNotImplementedError, Rulespec
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.plugins.lib.rulesets import load_and_transform, SKIP_ACTION
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateRulesets(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = load_and_transform(logger, use_git=active_config.wato_use_git)
        validate_rule_values(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


class UnparsableRuleValue(Exception):
    pass


def _validate_rule_value(rulespec: Rulespec, value: object) -> None:
    try:
        form_spec = rulespec.form_spec
    except FormSpecNotImplementedError:
        _validate_valuespec_value(rulespec.valuespec, value)
    else:
        _validate_form_spec_value(form_spec, RawDiskData(value))


def _validate_form_spec_value[T](form_spec: FormSpec[T], value: RawDiskData) -> None:
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=True))
    try:
        visitor.to_disk(value)
    except MKGeneralException as e:
        raise UnparsableRuleValue(str(e)) from e
    if validation_errors := visitor.validate(value):
        raise MKUserError(None, f"Validation errors: {validation_errors}")


def _validate_valuespec_value[T](valuespec: ValueSpec[T], value: T) -> None:
    try:
        valuespec.validate_datatype(value, "")
    except MKUserError as e:
        raise UnparsableRuleValue(str(e)) from e
    valuespec.validate_value(value, "")


def validate_rule_values(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    n_invalid, n_broken = 0, 0
    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in SKIP_ACTION:
            continue

        # Note: the rule values in these rulesets are already transformed
        # "thanks" to the load_and_transform call from above..
        for folder, index, rule in ruleset.get_rules():
            try:
                _validate_rule_value(ruleset.rulespec, rule.value)
            except MKUserError as excpt:
                n_invalid += 1
                logger.warning(
                    format_warning(
                        f"WARNING: Invalid rule configuration detected ({_make_rule_reference(ruleset, folder, index, excpt)})"
                    ),
                )

            except Exception as excpt:
                n_broken += 1
                logger.warning(
                    format_warning(
                        f"WARNING: Exception in ruleset implementation detected ({_make_rule_reference(ruleset, folder, index, excpt)})"
                    ),
                    exc_info=True,
                )
                identity = create_gui_crash_report().ident_to_text()
                logger.warning(f"A crash report was generated with ID: {identity}")

    if n_invalid:
        logger.warning(
            format_warning(
                "Detected %s issue(s) in configured rules.\n"
                "To correct these issues, we recommend to open the affected rules in the GUI.\n"
                "Upon attempting to save them, any problematic fields will be highlighted."
            ),
            n_invalid,
        )
    if n_broken:
        logger.warning(
            format_warning(
                "Detected %s issue(s) in loaded rulesets. This is a problem with the plug-in "
                "implementation. It needs to be addressed by the maintainers. Please review the "
                "crashes in the crash reports page to help fix the issues. "
                "Until all issues are resolved, we recommend disabling the affected rules."
            ),
            n_broken,
        )


def _make_rule_reference(ruleset: Ruleset, folder: Folder, index: int, excpt: Exception) -> str:
    return (
        f"Ruleset: {ruleset.name}, Title: {ruleset.title()}, Folder: {folder.path()},\n"
        f"Rule nr: {index}, Exception: {excpt}"
    )


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
        expiry_version=ExpiryVersion.NEVER,
    )
)
