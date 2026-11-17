#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

"""Script to validate if all available plug-ins can be loaded"""

import enum
import os
import sys
from argparse import ArgumentParser
from collections.abc import Callable, Container, Iterable, Mapping, Sequence
from typing import assert_never

from cmk.agent_based import v2 as agent_based_v2
from cmk.agent_based import v3_unstable as agent_based_v3_unstable
from cmk.bakery import v2 as bakery_v2
from cmk.base.api.bakery.register import (  # astrein: disable=module-layers
    load_bakery_plugins,
)
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import edition
from cmk.checkengine.plugin_backend import (  # astrein: disable=module-layers
    ENTRY_POINT_PREFIXES,
    extract_known_discovery_rulesets,
    load_all_plugins,
)

# TODO: Remove suppression for layer violation?
from cmk.checkengine.plugins import (  # astrein: disable=module-layers
    AgentBasedPlugins,
    CheckPlugin,
    InventoryPlugin,
    InventoryPluginName,
)

# TODO: Remove suppression for layer violation?
from cmk.checkengine.specs.checkresults import (  # astrein: disable=module-layers
    ActiveCheckResult,
)
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.graphing.v1 import entry_point_prefixes as graphing_entry_point_prefixes_v1
from cmk.graphing.v2_unstable import (
    entry_point_prefixes as graphing_entry_point_prefixes_v2_unstable,
)
from cmk.gui import main_modules  # astrein: disable=module-layers
from cmk.gui.form_specs import (  # astrein: disable=module-layers
    get_visitor,
    RawDiskData,
    VisitorOptions,
)
from cmk.gui.rule_specs.types import (  # astrein: disable=module-layers
    RuleSpec,
)
from cmk.gui.watolib.rulespecs import (  # astrein: disable=module-layers
    FormSpecNotImplementedError,
    Rulespec,
    rulespec_registry,
)
from cmk.gui.wsgi.app import (  # astrein: disable=module-layers
    gui_context,
)
from cmk.inventory_ui import v1 as inventory_ui_v1
from cmk.licensing.basics.options import (  # astrein: disable=module-layers
    get_license_options,
)
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.rulesets.v1 import entry_point_prefixes
from cmk.rulesets.v1.rule_specs import (
    ActiveCheck,
    CheckParameters,
    DiscoveryParameters,
    InventoryParameters,
    SpecialAgent,
)
from cmk.server_side_calls_backend import (  # astrein: disable=module-layers
    load_active_checks,
    load_special_agents,
)
from cmk.utils import paths

_AgentBasedPlugins = (
    agent_based_v2.SimpleSNMPSection
    | agent_based_v2.SNMPSection
    | agent_based_v2.AgentSection
    | agent_based_v2.CheckPlugin
    | agent_based_v3_unstable.CheckPlugin
    | agent_based_v3_unstable.MetricsSection
    | agent_based_v2.InventoryPlugin
)


class ValidationStep(enum.Enum):
    AGENT_BASED_PLUGINS = "agent based plugins loading"
    ACTIVE_CHECKS = "active checks loading"
    SPECIAL_AGENTS = "special agents loading"
    GRAPHING_PLUGINS = "graphing plugins loading"
    INVENTORY_UI_PLUGINS = "inventory view plugins loading"
    BAKERY_PLUGINS = "bakery plugins loading"
    BAKERY_RULE_SPECS = "bakery plugins rule specs validation"
    BAKERY_DEFAULT_PARAMETERS = "bakery plugins default parameters validation"
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


def _validate_agent_based_plugin_loading(
    *, debug: bool
) -> tuple[AgentBasedPlugins, ActiveCheckResult]:
    plugins = load_all_plugins(raise_errors=debug)
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


# Configured by top-level rule specs, see cmk/bakery/base/config.py
_TOP_LEVEL_BAKERY_RULE_SPECS: Mapping[str, str] = {
    "agent_encryption": "agent_encryption",
    "agent_port": "agent_ports",
}


def _unconfigurable_bakery_plugins(
    v1_plugin_names: Iterable[str],
    v2_plugins: Iterable[bakery_v2.BakeryPlugin],
    rule_spec_names: Container[str],
) -> Sequence[str]:
    """Names of bakery plug-ins that never run, as no rule spec configures them"""
    # Plug-ins with default parameters run without a rule, like check plug-ins without a ruleset
    candidates = {
        *v1_plugin_names,
        *(p.name for p in v2_plugins if p.default_parameters is None),
    }
    return sorted(
        name
        for name in candidates
        if RuleGroup.AgentConfig(name) not in rule_spec_names
        and _TOP_LEVEL_BAKERY_RULE_SPECS.get(name) not in rule_spec_names
    )


def _validate_bakery_plugins(*, debug: bool) -> Sequence[ActiveCheckResult]:
    plugins, failures = load_bakery_plugins()
    if failures and debug:
        raise failures[0][1]
    v2_discovered = discover_all_plugins(
        PluginGroup.BAKERY,
        bakery_v2.entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=debug,
    )
    return [
        to_result(
            ValidationStep.BAKERY_PLUGINS,
            [
                *(f"{module}: {exc}" for module, exc in failures),
                *(str(e) for e in v2_discovered.errors),
            ],
        ),
        to_result(
            ValidationStep.BAKERY_RULE_SPECS,
            [
                f"Bakery plug-in '{name}' never runs: there is no agent config rule spec '{name}'"
                for name in _unconfigurable_bakery_plugins(
                    plugins, v2_discovered.plugins.values(), rulespec_registry
                )
            ],
        ),
        _validate_bakery_default_parameters(v2_discovered.plugins.values(), debug=debug),
    ]


def _validate_bakery_default_parameters(
    plugins: Iterable[bakery_v2.BakeryPlugin], *, debug: bool
) -> ActiveCheckResult:
    if not os.environ.get("OMD_SITE"):
        return ActiveCheckResult(
            state=1,
            summary=f"{ValidationStep.BAKERY_DEFAULT_PARAMETERS.value.capitalize()} skipped",
            details=["Validation of default parameters can only be used as site user"],
        )

    errors = []
    with gui_context():
        for plugin in plugins:
            if (
                plugin.default_parameters is None
                or (rule_spec := rulespec_registry.get(RuleGroup.AgentConfig(plugin.name))) is None
            ):
                continue
            try:
                _validate_parameters(rule_spec, plugin.default_parameters)
            except Exception as e:
                if debug:
                    raise e
                errors.append(
                    f"Default parameters specified by {type(plugin).__name__} '{plugin.name}' "
                    f"cannot be read by AgentConfig rule spec '{plugin.name}': {e}"
                )
    return to_result(ValidationStep.BAKERY_DEFAULT_PARAMETERS, errors)


def _validate_graphing_plugin_loading(*, debug: bool) -> ActiveCheckResult:
    discovered_plugins = discover_all_plugins(
        PluginGroup.GRAPHING,
        dict(graphing_entry_point_prefixes_v1())
        | dict(graphing_entry_point_prefixes_v2_unstable()),
        skip_wrong_types=False,
        raise_errors=debug,
    )
    return to_result(ValidationStep.GRAPHING_PLUGINS, [str(e) for e in discovered_plugins.errors])


def _validate_inventory_ui_plugin_loading(*, debug: bool) -> ActiveCheckResult:
    discovered_plugins = discover_all_plugins(
        PluginGroup.INVENTORY_UI,
        inventory_ui_v1.entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=debug,
    )
    return to_result(
        ValidationStep.INVENTORY_UI_PLUGINS, [str(e) for e in discovered_plugins.errors]
    )


def _validate_rule_spec_loading() -> ActiveCheckResult:
    errors = [
        f"Error in rule spec {module_name}: {exc}"
        for path, subcomponent, module_name, exc in main_modules.get_failed_plugins()
    ]
    return to_result(ValidationStep.RULE_SPECS, errors)


def _validate_rule_spec_form_creation(*, debug: bool) -> ActiveCheckResult:
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
                try:
                    _ = loaded_rule_spec.form_spec
                except FormSpecNotImplementedError:
                    _ = loaded_rule_spec.valuespec
            except Exception as e:
                if debug:
                    raise e
                errors.append(f"{type(loaded_rule_spec).__name__} '{loaded_rule_spec.name}': {e}")
    return to_result(ValidationStep.RULE_SPEC_FORMS, errors)


def _validate_parameters(rule_spec: Rulespec, params: object) -> None:
    try:
        visitor = get_visitor(
            rule_spec.form_spec, VisitorOptions(mask_values=True, migrate_values=True)
        )
        validation_errors = visitor.validate(RawDiskData(params))
        if validation_errors:
            raise MKGeneralException(f"Validation Error {validation_errors}")
    except FormSpecNotImplementedError:
        rule_spec.valuespec.validate_datatype(params, "")
        rule_spec.valuespec.validate_value(params, "")


def _validate_agent_based_plugin_v2_ruleset_ref(
    plugin: _AgentBasedPlugins,
    *,
    rule_group: Callable[[str | None], str],
    fallback_rule_group: Callable[[str | None], str] | None = None,
    ruleset_ref_attr: str,
    default_params_attr: str,
    debug: bool,
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
        # we're validating against the enforced service rule in this case
        assert isinstance(plugin, (agent_based_v2.CheckPlugin, agent_based_v3_unstable.CheckPlugin))
        params = (plugin.name, "item" if "%s" in plugin.service_name else None, default_params)

    else:
        params = default_params

    try:
        _validate_parameters(rule_spec, params)
    except Exception as e:
        if debug:
            raise e
        return (
            f"Default parameters '{default_params_attr}' specified by {type(plugin).__name__} "
            f"'{plugin.name}' cannot be read by referenced rule spec '{ruleset_ref}': {e}"
        )
    return None


def _validate_referenced_rule_spec(*, debug: bool) -> ActiveCheckResult:
    if not os.environ.get("OMD_SITE"):
        return ActiveCheckResult(
            state=1,
            summary=f"{ValidationStep.RULE_SPEC_REFERENCED.value.capitalize()} skipped",
            details=["Validation of referenced rule specs can only be used as site user"],
        )

    # only for check API v2
    discovered_plugins: DiscoveredPlugins[_AgentBasedPlugins] = discover_all_plugins(
        PluginGroup.AGENT_BASED,
        ENTRY_POINT_PREFIXES,
        skip_wrong_types=False,
        raise_errors=False,  # already raised during loading validation if enabled
    )

    errors: list[str] = []

    with gui_context():
        for plugin in discovered_plugins.plugins.values():
            match plugin:
                case agent_based_v2.CheckPlugin() | agent_based_v3_unstable.CheckPlugin():
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=RuleGroup.DiscoveryParameters,
                            ruleset_ref_attr="discovery_ruleset_name",
                            default_params_attr="discovery_default_parameters",
                            debug=debug,
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
                            debug=debug,
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
                            debug=debug,
                        )
                    ) is not None:
                        errors.append(error)
                case (
                    agent_based_v2.SimpleSNMPSection()
                    | agent_based_v2.SNMPSection()
                    | agent_based_v2.AgentSection()
                    | agent_based_v3_unstable.MetricsSection()
                ):
                    if (
                        error := _validate_agent_based_plugin_v2_ruleset_ref(
                            plugin,
                            rule_group=RuleGroup.DiscoveryParameters,
                            ruleset_ref_attr="host_label_ruleset_name",
                            default_params_attr="host_label_default_parameters",
                            debug=debug,
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
        skip_wrong_types=False,
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
        skip_wrong_types=False,
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
        skip_wrong_types=False,
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
        skip_wrong_types=False,
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
        skip_wrong_types=False,
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


def validate_plugins(*, debug: bool) -> ActiveCheckResult:
    current_edition = edition(paths.omd_root)
    main_modules.register(current_edition, debug=debug)
    bakery_enabled = get_license_options(paths.omd_root, current_edition).bakery.enabled
    plugins, loading_subresult = _validate_agent_based_plugin_loading(debug=debug)
    sub_results = [
        loading_subresult,
        _validate_active_checks_loading(),
        _validate_special_agent_loading(),
        _validate_graphing_plugin_loading(debug=debug),
        _validate_inventory_ui_plugin_loading(debug=debug),
        _validate_rule_spec_loading(),
        _validate_rule_spec_form_creation(debug=debug),
        _validate_referenced_rule_spec(debug=debug),
        _validate_rule_spec_usage(plugins),
    ]
    if bakery_enabled:
        sub_results.extend(_validate_bakery_plugins(debug=debug))
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

    validation_result = validate_plugins(debug=args.debug)

    sys.stdout.write(f"{validation_result.as_text()}\n")
    return validation_result.state
