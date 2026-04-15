#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest

import cmk.config_anonymizer
import cmk.gui.wato._check_mk_configuration as _check_mk_configuration_module
import cmk.gui.wato._check_plugin_selection as _check_plugin_selection_module
import cmk.gui.watolib._autocompleters as _autocompleters_module
import cmk.gui.watolib.rulespecs as _rulespecs_module
from cmk.ccc import store
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.watolib.rulespecs import FormSpecNotImplementedError
from cmk.gui.watolib.utils import ALL_HOSTS, ALL_SERVICES, NEGATE

_DEFAULT_RULE_VALUES_PATH = Path(cmk.config_anonymizer.__file__).parent / "default_rule_values.mk"


class _DummyFolder:
    def path(self) -> str:
        return ""


def _build_check_info(
    plugins: AgentBasedPlugins,
) -> Mapping[CheckPluginName, Mapping[str, str]]:
    """Build check plugin info the same way the get-check-information automation does,
    without requiring a running automation helper."""
    plugin_infos: dict[str, dict[str, str]] = {}
    for plugin in plugins.check_plugins.values():
        plugin_info = plugin_infos.setdefault(
            str(plugin.name),
            {
                "title": str(plugin.name),
                "name": str(plugin.name),
                "service_description": str(plugin.service_name),
            },
        )
        if plugin.check_ruleset_name:
            plugin_info["group"] = str(plugin.check_ruleset_name)
    return {CheckPluginName(name): info for name, info in sorted(plugin_infos.items())}


def _build_section_info(plugins: AgentBasedPlugins) -> Mapping[str, Mapping[str, str]]:
    """Build section info the same way the get-section-information automation does,
    without requiring a running automation helper."""
    section_infos: dict[str, dict[str, str]] = {
        str(name): {"name": str(name), "type": "agent"} for name in plugins.agent_sections
    }
    section_infos.update(
        {str(name): {"name": str(name), "type": "snmp"} for name in plugins.snmp_sections}
    )
    return section_infos


@pytest.mark.usefixtures("request_context")
def test_default_rule_values_are_valid(
    monkeypatch: pytest.MonkeyPatch,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    # Provide check/section plugin info built directly from loaded plugins, bypassing
    # the automation socket calls that the cached functions normally make.
    check_info = _build_check_info(agent_based_plugins)
    section_info = _build_section_info(agent_based_plugins)
    for _mod in (_rulespecs_module, _check_plugin_selection_module, _autocompleters_module):
        monkeypatch.setattr(_mod, "get_check_information_cached", lambda *, debug: check_info)
    monkeypatch.setattr(
        _check_mk_configuration_module,
        "get_section_information_cached",
        lambda *, debug: section_info,
    )

    loaded_config = store.load_mk_file(
        _DEFAULT_RULE_VALUES_PATH,
        default={
            "ALL_HOSTS": ALL_HOSTS,
            "ALL_SERVICES": ALL_SERVICES,
            "NEGATE": NEGATE,
            "FOLDER_PATH": "",
            **RulesetCollection._prepare_empty_rulesets(),
        },
        lock=False,
    )

    folder = _DummyFolder()
    rulesets = RulesetCollection(RulesetCollection._initialize_rulesets())
    rulesets.replace_folder_config(folder, loaded_config)  # type: ignore[arg-type]

    # These rulesets require site-specific data (groups, attributes, icons) to be
    # configured in order to pass validation. They cannot be validated without a running site.
    skip_rulesets = {
        "service_groups",
        "host_contactgroups",
        "service_contactgroups",
        "custom_service_attributes",
        "extra_service_conf:icon_image",
    }

    # Check groups available in the current edition (from the loaded plugins).
    available_check_groups = {info["group"] for info in check_info.values() if "group" in info}

    validation_errors: list[tuple[str, str]] = []
    for ruleset in rulesets.get_rulesets().values():
        if ruleset.name in skip_rulesets:
            continue
        # static_checks:X validate against check plugins in group X. Skip if no plugins for
        # that group are available in the current edition (e.g. pro-only check plugins).
        if ruleset.name.startswith("static_checks:"):
            check_group = ruleset.name.split(":", 1)[1]
            if check_group not in available_check_groups:
                continue
        for _folder, _index, rule in ruleset.get_rules():
            try:
                try:
                    visitor = get_visitor(
                        ruleset.rulespec.form_spec,
                        VisitorOptions(migrate_values=False, mask_values=True),
                    )
                    errors = visitor.validate(RawDiskData(rule.value))
                    if errors:
                        validation_errors.append((ruleset.name, str(errors)))
                except FormSpecNotImplementedError:
                    ruleset.rulespec.valuespec.validate_datatype(rule.value, "")
                    ruleset.rulespec.valuespec.validate_value(rule.value, "")
            except MKUserError as e:
                validation_errors.append((ruleset.name, str(e)))

    assert validation_errors == []
