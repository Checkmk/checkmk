#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import re
from collections.abc import Mapping, Sequence

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary as LegacyDictionary
from cmk.gui.valuespec import (
    ListChoice,
    ListOf,
    MonitoringState,
    TextInput,
    TextOrRegExp,
)
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FieldSize,
    FixedValue,
    IECMagnitude,
    InputHint,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    MultipleChoice,
    MultipleChoiceElement,
    ServiceState,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _valuespec_discovery_systemd_units_services_rules() -> LegacyDictionary:
    return LegacyDictionary(
        title=_("Systemd single services discovery"),
        elements=[
            (
                "descriptions",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by description"),
                    help=_("Restrict the systemd services by description."),
                    allow_empty=False,
                ),
            ),
            (
                "names",
                ListOf(
                    valuespec=TextOrRegExp(),
                    title=_("Restrict by service unit name"),
                    help=_("Restrict the systemd services by unit name."),
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
        ],
        help=_(
            "Configure the discovery of single systemd services. To be discovered, a service "
            "must match at least one description condition, one name condition and one state "
            "condition, if configured. To simply discover all systemd services, do not "
            "configure any restrictions. Note that independently of this rule set, some systemd "
            "service units which are used by the Checkmk agent ('check-mk-agent@...') will "
            "never be discovered because they appear and disappear frequently."
        ),
        empty_text=_("No restrictions (discover all systemd service units)"),
    )


rulespec_registry.register(
    HostRulespec(
        is_deprecated=True,
        title=lambda: _("Systemd single services discovery"),
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="discovery_systemd_units_services_rules",
        valuespec=_valuespec_discovery_systemd_units_services_rules,
    )
)


def _migrate_to_match(value: object) -> Mapping[str, object]:
    match value:
        case str() if value.startswith("~"):
            return {"match": "regex", "pattern": value[1:]}
        case str():
            return {"match": "exact", "pattern": value}
        case dict():
            return value
        case _:
            raise TypeError(value)


def _migrate_to_label_list(value: object) -> Sequence[Mapping[str, object]]:
    match value:
        case dict():
            return [{"key": key, "value": label_value} for key, label_value in value.items()]
        case list():
            return value
        case _:
            raise TypeError(value)


def _validate_regex_pattern(value: Mapping[str, object]) -> None:
    if value["match"] != "regex":
        return
    try:
        re.compile(str(value["pattern"]))
    except re.error:
        raise validators.ValidationError(
            Message("Invalid regular expression: %s") % str(value["pattern"])
        )


def _unit_match(title: Title, help_text: Help) -> List[Mapping[str, object]]:
    return List(
        title=title,
        help_text=help_text,
        element_template=Dictionary(
            elements={
                "pattern": DictElement(
                    group=DictGroup(),
                    parameter_form=String(
                        title=Title("Pattern"),
                        field_size=FieldSize.LARGE,
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                    required=True,
                ),
                "match": DictElement(
                    group=DictGroup(),
                    parameter_form=SingleChoice(
                        title=Title("Match type"),
                        help_text=Help(
                            "With an explicit match, the pattern must equal the whole text."
                            " With a regular expression match, the pattern is a regular"
                            " expression that is matched from the beginning. Add a trailing"
                            " <tt>$</tt> to match the whole text. Read more about"
                            " [regexes|regular expression matching in Checkmk] in our User Guide."
                        ),
                        elements=[
                            SingleChoiceElement(name="exact", title=Title("Explicit match")),
                            SingleChoiceElement(
                                name="regex", title=Title("Regular expression match")
                            ),
                        ],
                        prefill=DefaultValue("exact"),
                    ),
                    required=True,
                ),
            },
            custom_validate=(_validate_regex_pattern,),
            migrate=_migrate_to_match,
        ),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def _unit_restriction_elements() -> Mapping[str, DictElement]:
    return {
        "descriptions": DictElement(
            parameter_form=_unit_match(
                Title("Restrict by description"),
                Help("Restrict the systemd units by description."),
            ),
        ),
        "names": DictElement(
            parameter_form=_unit_match(
                Title("Restrict by name"),
                Help("Restrict the systemd units by their name."),
            ),
        ),
        "states": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Restrict by state"),
                elements=[
                    MultipleChoiceElement(name="active", title=Title("active")),
                    MultipleChoiceElement(name="inactive", title=Title("inactive")),
                    MultipleChoiceElement(name="failed", title=Title("failed")),
                ],
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
    }


def _host_label_elements() -> Mapping[str, DictElement]:
    return {
        "host_labels_auto": DictElement(
            parameter_form=FixedValue(
                value=None,
                title=Title("Automatic generation of host labels"),
                help_text=Help(
                    "Create host labels for each discovered systemd service in the following"
                    " format %r"
                )
                % "cmk/systemd/unit/<name>:yes",
            ),
        ),
        "host_labels_explicit": DictElement(
            parameter_form=List(
                title=Title("Explicit host labels"),
                help_text=Help(
                    "Here, you can specify host labels that are automatically created, when one of"
                    " the systemd services is discovered."
                ),
                element_template=Dictionary(
                    elements={
                        "key": DictElement(
                            parameter_form=String(
                                title=Title("Key"),
                                custom_validate=(
                                    validators.MatchRegex(
                                        "^[^:]+$",
                                        Message("The key must not be empty or contain a colon."),
                                    ),
                                ),
                            ),
                            required=True,
                        ),
                        "value": DictElement(
                            parameter_form=String(
                                title=Title("Value"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                    },
                ),
                migrate=_migrate_to_label_list,
            ),
        ),
    }


def _discovery_form(elements: Mapping[str, DictElement]) -> Dictionary:
    return Dictionary(
        title=Title("Systemd single unit discovery"),
        help_text=Help(
            "Configure the discovery of single systemd units (sockets or services)."
            " To be discovered, a unit must match at least one condition each: "
            "one description condition, one name condition and one state condition, if configured."
            " To discover all units, do not configure any restrictions."
            " Independently of this rule set, some systemd units created by the Checkmk agent"
            " ('check-mk-agent@...') will never be discovered."
            " They appear and disappear frequently."
        ),
        no_elements_text=Message("No restrictions (discover all units)"),
        elements=elements,
    )


def _parameter_form_discovery_systemd_units_services() -> Dictionary:
    return _discovery_form({**_unit_restriction_elements(), **_host_label_elements()})


def _parameter_form_discovery_systemd_units_sockets() -> Dictionary:
    return _discovery_form(_unit_restriction_elements())


rule_spec_discovery_systemd_units_services = DiscoveryParameters(
    name="discovery_systemd_units_services",
    title=Title("Systemd single service discovery"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_discovery_systemd_units_services,
)

rule_spec_discovery_systemd_units_sockets = DiscoveryParameters(
    name="discovery_systemd_units_sockets",
    title=Title("Systemd single socket discovery"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_discovery_systemd_units_sockets,
)


def _parameter_valuespec_systemd_services():
    return LegacyDictionary(
        elements=[
            (
                "states",
                LegacyDictionary(
                    title=_("Map systemd states to monitoring states"),
                    elements=[
                        (
                            "active",
                            MonitoringState(
                                title=_("Monitoring state if service is active"),
                                default_value=0,
                            ),
                        ),
                        (
                            "inactive",
                            MonitoringState(
                                title=_("Monitoring state if service is inactive"),
                                default_value=0,
                            ),
                        ),
                        (
                            "failed",
                            MonitoringState(
                                title=_("Monitoring state if service is failed"),
                                default_value=2,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "states_default",
                MonitoringState(
                    title=_("Monitoring state for any other service state"),
                    default_value=2,
                ),
            ),
            (
                "else",
                MonitoringState(
                    title=_("Monitoring state if a monitored service is not found at all."),
                    default_value=2,
                ),
            ),
        ],
        help=_(
            "This rule set only applies when individual systemd services are discovered. "
            "The user needs to configure this option in the discovery section."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        is_deprecated=True,
        check_group_name="systemd_services",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the service")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_systemd_services,
        title=lambda: _("Systemd single services"),
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
