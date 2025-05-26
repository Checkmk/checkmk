#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Script to validate if all available plug-ins can be loaded"""

import enum
import os
import sys
from argparse import ArgumentParser
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import assert_never

from cmk.ccc import debug

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.checkresults import (  # pylint: disable=cmk-module-layer-violation
    ActiveCheckResult,
)
from cmk.checkengine.plugin_backend import (  # pylint: disable=cmk-module-layer-violation
    extract_known_discovery_rulesets,
)
from cmk.checkengine.plugins import (  # pylint: disable=cmk-module-layer-violation  # pylint: disable=cmk-module-layer-violation
    AgentBasedPlugins,
    CheckPlugin,
    InventoryPlugin,
    InventoryPluginName,
)

from cmk.base.config import (  # pylint: disable=cmk-module-layer-violation
    load_all_pluginX,
)

from cmk.gui.main_modules import load_plugins  # pylint: disable=cmk-module-layer-violation
from cmk.gui.utils import get_failed_plugins  # pylint: disable=cmk-module-layer-violation
from cmk.gui.utils.rule_specs.loader import RuleSpec  # pylint: disable=cmk-module-layer-violation
from cmk.gui.utils.script_helpers import gui_context  # pylint: disable=cmk-module-layer-violation
from cmk.gui.watolib.rulespecs import (  # pylint: disable=cmk-module-layer-violation
    rulespec_registry,
)

from cmk.agent_based import v2 as agent_based_v2
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.rulesets.v1 import entry_point_prefixes
from cmk.rulesets.v1.rule_specs import (
    ActiveCheck,
    CheckParameters,
    DiscoveryParameters,
    InventoryParameters,
    SpecialAgent,
)
from cmk.server_side_calls_backend import (  # pylint: disable=cmk-module-layer-violation
    load_active_checks,
    load_special_agents,
)

_AgentBasedPlugins = (
    agent_based_v2.SimpleSNMPSection
    | agent_based_v2.SNMPSection
    | agent_based_v2.AgentSection
    | agent_based_v2.CheckPlugin
    | agent_based_v2.InventoryPlugin
)


class ValidationStep(enum.Enum):
    AGENT_BASED_PLUGINS = "agent based plugins loading"
    ACTIVE_CHECKS = "active checks loading"
    SPECIAL_AGENTS = "special agents loading"
    RULE_SPECS = "rule specs loading"
    RULE_SPEC_FORMS = "rule specs forms creation"
    RULE_SPEC_REFERENCED = "referenced rule specs validation"
    RULE_SPEC_USED = "loaded rule specs usage"


def to_result(step: ValidationStep, errors: Sequence[str]) -> ActiveCheckResult:
    return ActiveCheckResult(
        state=2 if errors else 0,
        summary=(
            f"{step.value.capitalize()} failed"
            if errors
            else f"{step.value.capitalize()} succeeded"
        ),
        details=list(errors),
    )


def _validate_agent_based_plugin_loading() -> tuple[AgentBasedPlugins, ActiveCheckResult]:
    plugins = load_all_pluginX(paths.checks_dir)
    return plugins, to_result(ValidationStep.AGENT_BASED_PLUGINS, plugins.errors)


def _validate_active_checks_loading() -> ActiveCheckResult:
    try:
        _ = load_active_checks(raise_errors=True)
    except Exception as error:
        errors = [f"At least one error: {error}"]
    else:
        errors = []
    return to_result(ValidationStep.ACTIVE_CHECKS, errors)


def _validate_special_agent_loading() -> ActiveCheckResult:
    try:
        _ = load_special_agents(raise_errors=True)
    except Exception as error:
        errors = [f"At least one error: {error}"]
    else:
        errors = []
    return to_result(ValidationStep.SPECIAL_AGENTS, errors)


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


def _validate_agent_based_plugin_v2_ruleset_ref(
    plugin: _AgentBasedPlugins,
    *,
    rule_group: Callable[[str | None], str],
    fallback_rule_group: Callable[[str | None], str] | None = None,
    ruleset_ref_attr: str,
    default_params_attr: str,
) -> str | None:
    if (ruleset_ref := getattr(plugin, ruleset_ref_attr)) is None:
        return None

    if (default_params := getattr(plugin, default_params_attr)) is None:
        return (
            f"Default parameters '{default_params_attr}' specified by {type(plugin).__name__} "
            f"'{plugin.name}' should not be `None` since there is a ruleset ('{ruleset_ref}')"
        )

    if (rule_spec := rulespec_registry.get(rule_group(ruleset_ref))) is None:
        if (
            fallback_rule_group is None
            or (rule_spec := rulespec_registry.get(fallback_rule_group(ruleset_ref))) is None
        ):
            return (
                f"'{ruleset_ref_attr}' of {type(plugin).__name__} '{plugin.name}' references "
                f"non-existent rule spec '{ruleset_ref}'"
            )
        # we're validating against the enforces service rule in this case
        assert isinstance(plugin, agent_based_v2.CheckPlugin)
        params = (plugin.name, "item" if "%s" in plugin.service_name else None, default_params)

    else:
        params = default_params

    try:
        rule_spec.valuespec.validate_datatype(params, "")
        rule_spec.valuespec.validate_value(params, "")
    except Exception as e:
        if debug.enabled():
            raise e
        return (
            f"Default parameters '{default_params_attr}' specified by {type(plugin).__name__} "
            f"'{plugin.name}' cannot be read by referenced rule spec '{ruleset_ref}': {e}"
        )
    return None


def _validate_referenced_rule_spec() -> ActiveCheckResult:
    if not os.environ.get("OMD_SITE"):
        return ActiveCheckResult(
            state=1,
            summary=f"{ValidationStep.RULE_SPEC_REFERENCED.value.capitalize()} skipped",
            details=["Validation of referenced rule specs can only be used as site user"],
        )

    # only for check API v2
    discovered_plugins: DiscoveredPlugins[_AgentBasedPlugins] = discover_all_plugins(
        PluginGroup.AGENT_BASED,
        agent_based_v2.entry_point_prefixes(),
        raise_errors=False,  # already raised during loading validation if enabled
    )

    errors: list[str] = []

    with gui_context():
        for plugin in discovered_plugins.plugins.values():
            match plugin:
                case agent_based_v2.CheckPlugin():
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=lambda x: f"{x}",
                            ruleset_ref_attr="discovery_ruleset_name",
                            default_params_attr="discovery_default_parameters",
                        )
                    ) is not None:
                        errors.append(error)
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=RuleGroup.CheckgroupParameters,
                            fallback_rule_group=RuleGroup.StaticChecks,
                            ruleset_ref_attr="check_ruleset_name",
                            default_params_attr="check_default_parameters",
                        )
                    ) is not None:
                        errors.append(error)
                case agent_based_v2.InventoryPlugin():
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=RuleGroup.InvParameters,
                            ruleset_ref_attr="inventory_ruleset_name",
                            default_params_attr="inventory_default_parameters",
                        )
                    ) is not None:
                        errors.append(error)
                case (
                    agent_based_v2.SimpleSNMPSection()
                    | agent_based_v2.SNMPSection()
                    | agent_based_v2.AgentSection()
                ):
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=lambda x: f"{x}",
                            ruleset_ref_attr="host_label_ruleset_name",
                            default_params_attr="host_label_default_parameters",
                        )
                    ) is not None:
                        errors.append(error)

                case other:
                    assert_never(other)

    return to_result(ValidationStep.RULE_SPEC_REFERENCED, errors)


def _check_if_referenced(
    discovered_plugins: DiscoveredPlugins[RuleSpec], referenced_ruleset_names: set[str]
) -> list[str]:
    reference_errors = []
    for plugin in discovered_plugins.plugins.values():
        if plugin.is_deprecated:
            continue

        if plugin.name not in referenced_ruleset_names:
            reference_errors.append(
                f"{type(plugin).__name__} rule set '{plugin.name}' is not used anywhere. Ensure "
                f"the correct spelling at the referencing plug-in or deprecate the ruleset"
            )
    return reference_errors


def _validate_check_parameters_usage(check_plugins: Iterable[CheckPlugin]) -> Sequence[str]:
    discovered_check_parameters: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        {CheckParameters: entry_point_prefixes()[CheckParameters]},
        raise_errors=False,
    )

    referenced_ruleset_names = {
        str(plugin.check_ruleset_name)
        for plugin in check_plugins
        if plugin.check_ruleset_name is not None
    }
    return _check_if_referenced(discovered_check_parameters, referenced_ruleset_names)


def _validate_discovery_parameters_usage(
    plugins: AgentBasedPlugins,
) -> Sequence[str]:
    discovered_discovery_parameters: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        {DiscoveryParameters: entry_point_prefixes()[DiscoveryParameters]},
        raise_errors=False,
    )
    referenced_ruleset_names = {
        str(ruleset_name) for ruleset_name in extract_known_discovery_rulesets(plugins)
    }
    return _check_if_referenced(discovered_discovery_parameters, referenced_ruleset_names)


def _validate_inventory_parameters_usage(
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
) -> Sequence[str]:
    discovered_inventory_parameters: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        {InventoryParameters: entry_point_prefixes()[InventoryParameters]},
        raise_errors=False,
    )
    referenced_ruleset_names = {
        str(plugin.ruleset_name)
        for plugin in inventory_plugins.values()
        if plugin.ruleset_name is not None
    }
    return _check_if_referenced(discovered_inventory_parameters, referenced_ruleset_names)


def _validate_active_check_usage() -> Sequence[str]:
    discovered_active_checks: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        {ActiveCheck: entry_point_prefixes()[ActiveCheck]},
        raise_errors=False,
    )
    referenced_ruleset_names = {
        active_check.name for active_check in load_active_checks(raise_errors=False).values()
    }
    return _check_if_referenced(discovered_active_checks, referenced_ruleset_names)


def _validate_special_agent_usage() -> Sequence[str]:
    discovered_special_agents: DiscoveredPlugins[RuleSpec] = discover_all_plugins(
        PluginGroup.RULESETS,
        {SpecialAgent: entry_point_prefixes()[SpecialAgent]},
        raise_errors=False,
    )
    referenced_ruleset_names = {
        active_check.name for active_check in load_special_agents(raise_errors=False).values()
    }
    return _check_if_referenced(discovered_special_agents, referenced_ruleset_names)


def _validate_rule_spec_usage(plugins: AgentBasedPlugins) -> ActiveCheckResult:
    # only for ruleset API v1
    errors: list[str] = []

    errors.extend(_validate_check_parameters_usage(plugins.check_plugins.values()))
    errors.extend(_validate_discovery_parameters_usage(plugins))
    errors.extend(_validate_inventory_parameters_usage(plugins.inventory_plugins))
    errors.extend(_validate_active_check_usage())
    errors.extend(_validate_special_agent_usage())

    return to_result(ValidationStep.RULE_SPEC_USED, errors)


def validate_plugins() -> ActiveCheckResult:
    plugins, loading_subresult = _validate_agent_based_plugin_loading()
    sub_results = [
        loading_subresult,
        _validate_active_checks_loading(),
        _validate_special_agent_loading(),
        _validate_rule_spec_loading(),
        _validate_rule_spec_form_creation(),
        _validate_referenced_rule_spec(),
        _validate_rule_spec_usage(plugins),
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

    sys.stdout.write(f"{validation_result.as_text()}\n")
    return validation_result.state
