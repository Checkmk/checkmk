#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from typing import Callable

from cmk.gui import valuespec as legacy_valuespecs
from cmk.gui import wato
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib.rulespecs import CheckParameterRulespecWithItem

from cmk.rulesets import v1 as ruleset_api_v1
from cmk.rulesets.v1 import RuleSpecSubGroup

_RULESPEC_SUB_GROUP_LEGACY_MAPPING = {
    RuleSpecSubGroup.CHECK_PARAMETERS_APPLICATIONS: wato.RulespecGroupCheckParametersApplications
}


def _localize_optional(
    to_localize: ruleset_api_v1.Localizable | None, localizer: Callable[[str], str]
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: ruleset_api_v1.RuleSpec, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    if isinstance(to_convert, ruleset_api_v1.CheckParameterRuleSpecWithItem):
        return CheckParameterRulespecWithItem(
            check_group_name=to_convert.name,
            title=None
            if to_convert.title is None
            else partial(to_convert.title.localize, localizer),
            group=_convert_to_legacy_rulespec_group(to_convert.group),
            item_spec=partial(_convert_to_legacy_item_spec, to_convert.item, localizer),
            match_type="dict",
            parameter_valuespec=partial(
                _convert_to_legacy_valuespec, to_convert.value_spec(), localizer
            ),
            create_manual_check=False,  # TODO create EnforcedService explicitly and convert
        )

    raise NotImplementedError(to_convert)


def _convert_to_legacy_rulespec_group(
    to_convert: ruleset_api_v1.RuleSpecCustomSubGroup | ruleset_api_v1.RuleSpecSubGroup,
) -> type[legacy_rulespecs.RulespecSubGroup]:
    if isinstance(to_convert, ruleset_api_v1.RuleSpecSubGroup):
        return _RULESPEC_SUB_GROUP_LEGACY_MAPPING[to_convert]
    raise ValueError(to_convert)


@dataclass(frozen=True)
class _LegacyDictKeyProps:
    required: list[str]
    ignored: list[str]
    show_more: list[str]


def _extract_key_props(
    dic_elements: Mapping[str, ruleset_api_v1.DictElement]
) -> _LegacyDictKeyProps:
    key_props = _LegacyDictKeyProps(required=[], ignored=[], show_more=[])

    for key, dic_elem in dic_elements.items():
        if dic_elem.required:
            key_props.required.append(key)
        if dic_elem.ignored:
            key_props.ignored.append(key)
        if dic_elem.show_more:
            key_props.show_more.append(key)

    return key_props


def _convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.ValueSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    if isinstance(to_convert, ruleset_api_v1.Dictionary):
        elements = [
            (key, _convert_to_legacy_valuespec(elem.spec, localizer))
            for key, elem in to_convert.elements.items()
        ]

        legacy_key_props = _extract_key_props(to_convert.elements)

        return legacy_valuespecs.Dictionary(
            elements=elements,
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
            empty_text=_localize_optional(to_convert.no_elements_text, localizer),
            required_keys=legacy_key_props.required,
            ignored_keys=legacy_key_props.ignored,
            show_more_keys=legacy_key_props.show_more,
        )
    if isinstance(to_convert, ruleset_api_v1.MonitoringState):
        return legacy_valuespecs.MonitoringState(
            title=to_convert.title.localize(localizer),
            default_value=to_convert.default_value.value,
        )

    raise NotImplementedError(to_convert)


def _convert_to_legacy_item_spec(
    to_convert: ruleset_api_v1.ItemSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput | legacy_valuespecs.DropdownChoice:
    if isinstance(to_convert, ruleset_api_v1.TextInput):
        return legacy_valuespecs.TextInput(
            title=_localize_optional(to_convert.title, localizer),
        )
    raise NotImplementedError(to_convert)
