#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary as LegacyDictionary
from cmk.gui.valuespec import (
    FixedValue,
    Labels,
    ListChoice,
    ListOf,
    TextOrRegExp,
    ValueSpec,
)
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _valuespec_discovery_systemd_units_host_labels() -> list[tuple[str, ValueSpec]]:
    return [
        (
            "host_labels_auto",
            FixedValue(
                True,
                title=_("Automatic generation of host labels"),
                totext=_("active"),
                help=_(
                    "Create host labels for each discovered systemd service in the following"
                    " format %(label_format)r"
                )
                % {"label_format": "cmk/systemd/unit/<name>:yes"},
            ),
        ),
        (
            "host_labels_explicit",
            Labels(
                Labels.World.CONFIG,
                title=_("Explicit host labels"),
                help=_(
                    "Here, you can specify host labels that are automatically created, when one of"
                    " the systemd services is discovered."
                ),
            ),
        ),
    ]


def _valuespec_discovery_systemd_units_elements() -> list:
    return [
        (
            "descriptions",
            ListOf(
                valuespec=TextOrRegExp(),
                title=_("Restrict by description"),
                help=_("Restrict the systemd units by description."),
                allow_empty=False,
            ),
        ),
        (
            "names",
            ListOf(
                valuespec=TextOrRegExp(),
                title=_("Restrict by name"),
                help=_("Restrict the systemd units by their name."),
                allow_empty=False,
            ),
        ),
        (
            "states",
            ListChoice(
                choices=[
                    ("active", "active"),
                    ("inactive", "inactive"),
                    ("failed", "failed"),
                ],
                title=_("Restrict by state"),
                allow_empty=False,
            ),
        ),
    ]


def _valuespec_discovery_systemd_units_base(
    elements: list[tuple[str, ValueSpec]],
) -> LegacyDictionary:
    return LegacyDictionary(
        title=_("Systemd single unit discovery"),
        elements=elements,
        help=_(
            "Configure the discovery of single systemd units (sockets or services)."
            " To be discovered, a unit must match at least one condition each: "
            "one description condition, one name condition and one state condition, if configured."
            " To discover all units, do not configure any restrictions."
            " Independently of this rule set, some systemd units created by the Checkmk agent"
            " ('check-mk-agent@...') will never be discovered."
            " They appear and disappear frequently."
        ),
        empty_text=_("No restrictions (discover all units)"),
    )


def _valuespec_discovery_systemd_units_addon() -> LegacyDictionary:
    return _valuespec_discovery_systemd_units_base(
        _valuespec_discovery_systemd_units_elements()
        + _valuespec_discovery_systemd_units_host_labels()
    )


def _valuespec_discovery_systemd_units() -> LegacyDictionary:
    return _valuespec_discovery_systemd_units_base(_valuespec_discovery_systemd_units_elements())


rulespec_registry.register(
    HostRulespec(
        title=lambda: _("Systemd single service discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name=RuleGroup.DiscoveryParameters("discovery_systemd_units_services"),
        valuespec=_valuespec_discovery_systemd_units_addon,
    )
)

rulespec_registry.register(
    HostRulespec(
        title=lambda: _("Systemd single socket discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name=RuleGroup.DiscoveryParameters("discovery_systemd_units_sockets"),
        valuespec=_valuespec_discovery_systemd_units,
    )
)


_TIME_MAGNITUDES = [TimeMagnitude.MINUTE, TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND]


def _time_levels(title: Title, help_text: Help, direction: LevelDirection) -> SimpleLevels[float]:
    return SimpleLevels(
        title=title,
        help_text=help_text,
        level_direction=direction,
        form_spec_template=TimeSpan(displayed_magnitudes=_TIME_MAGNITUDES),
        prefill_fixed_levels=InputHint((0.0, 0.0)),
        migrate=migrate_to_float_simple_levels,
    )


def _migrate_unit_not_found_key(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    return {("unit_not_found" if key == "else" else key): v for key, v in value.items()}


def _parameter_form_systemd_units() -> Dictionary:
    return Dictionary(
        elements={
            "states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map systemd states to monitoring states"),
                    elements={
                        "active": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is active"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "inactive": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is inactive"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "failed": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is failed"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                    },
                ),
            ),
            "states_default": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state for any other unit state"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "unit_not_found": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state if a monitored unit is not found at all"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "memory": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Memory upper levels"),
                    help_text=Help("Define the upper levels for memory usage."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ]
                    ),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "cpu_time": DictElement(
                parameter_form=_time_levels(
                    Title("CPU time upper levels"),
                    Help("Define the upper levels for the consumed CPU time."),
                    LevelDirection.UPPER,
                ),
            ),
            "active_since_lower": DictElement(
                parameter_form=_time_levels(
                    Title("Lower levels for the time the service is active"),
                    Help(
                        "Define the lower levels for the time, the systemd service is active since."
                    ),
                    LevelDirection.LOWER,
                ),
            ),
            "active_since_upper": DictElement(
                parameter_form=_time_levels(
                    Title("Upper levels for the time the service is active"),
                    Help(
                        "Define the upper levels for the time, the systemd service is active since."
                    ),
                    LevelDirection.UPPER,
                ),
            ),
        },
        help_text=Help(
            "This rule set only applies when individual systemd units are discovered. "
            "The user needs to configure this option in the discovery section."
        ),
        migrate=_migrate_unit_not_found_key,
    )


rule_spec_systemd_units_services = CheckParameters(
    name="systemd_units_services",
    title=Title("Systemd single service"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_systemd_units,
    condition=HostAndItemCondition(item_title=Title("Name of the service")),
)

rule_spec_systemd_units_sockets = CheckParameters(
    name="systemd_units_sockets",
    title=Title("Systemd single socket"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_systemd_units,
    condition=HostAndItemCondition(item_title=Title("Name of the socket")),
)
