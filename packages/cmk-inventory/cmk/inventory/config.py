#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NotRequired, TypedDict


class _RawIntervalFromConfigMandatory(TypedDict):
    interval: int
    visible_raw_path: str


class RawIntervalFromConfig(_RawIntervalFromConfigMandatory, total=False):
    attributes: Literal["all"] | tuple[str, list[str]]
    columns: Literal["all"] | tuple[str, list[str]]


NothingOrChoices = Literal["nothing"] | tuple[Literal["choices"], Sequence[str]]


class PermittedPath(TypedDict):
    visible_raw_path: str
    attributes: NotRequired[NothingOrChoices]
    columns: NotRequired[NothingOrChoices]
    nodes: NotRequired[NothingOrChoices]


InventoryPathsConfig = (
    Literal["allow_all", "forbid_all"] | tuple[Literal["paths"], list[PermittedPath]]
)


class InvCleanupParamsCombined(TypedDict):
    strategy: Literal["and", "or"]
    file_age: int
    number_of_history_entries: int


type InvCleanupParamsChoice = (
    tuple[Literal["file_age"], int]
    | tuple[Literal["number_of_history_entries"], int]
    | tuple[Literal["combined"], InvCleanupParamsCombined]
)


class InvCleanupParamsOfHosts(TypedDict):
    regex_or_explicit: Sequence[str]
    parameters: InvCleanupParamsChoice


class InvCleanupParamsDefaultCombined(TypedDict):
    strategy: Literal["and"]
    file_age: int
    number_of_history_entries: int


class InvCleanupParams(TypedDict):
    for_hosts: Sequence[InvCleanupParamsOfHosts]
    default: InvCleanupParamsDefaultCombined | None
    abandoned_file_age: int


type LabelPickerCaseConversion = Literal["no_conversion", "lower", "upper"]


class LabelPickerConfigCaseConversion(TypedDict):
    label: LabelPickerCaseConversion
    value: LabelPickerCaseConversion


class LabelPickerConfigValueMatch(TypedDict):
    value_match: str


class LabelPickerConfigReplaceRule(TypedDict):
    value_match: str
    value_replacement: str


type LabelPickerConfigValueMatchOrReplace = (
    tuple[Literal["use_value"], None]
    | tuple[Literal["use_value_if_matches"], LabelPickerConfigValueMatch]
    | tuple[Literal["match_and_replace_value"], Sequence[LabelPickerConfigReplaceRule]]
)


class LabelPickerConfigAttribute(TypedDict):
    label_name: str
    key_match: str
    value_match: LabelPickerConfigValueMatchOrReplace


class LabelPickerConfigRowMatch(TypedDict):
    column: str
    value_match: str


type LabelPickerConfigRowFilter = (
    tuple[Literal["all_rows"], None] | tuple[Literal["matching_rows"], LabelPickerConfigRowMatch]
)


class LabelPickerConfigColumn(TypedDict):
    label_name: str
    column: str
    row_filter: LabelPickerConfigRowFilter
    value_match: LabelPickerConfigValueMatchOrReplace


class LabelPickerSource(TypedDict):
    path: str
    attributes: Sequence[LabelPickerConfigAttribute]
    columns: Sequence[LabelPickerConfigColumn]


class LabelPickerLabeling(TypedDict):
    label_prefix: str
    case_conversion: LabelPickerConfigCaseConversion


class LabelPickerConfig(TypedDict):
    source: LabelPickerSource
    labeling: LabelPickerLabeling


class LabelPickerRuleValue(TypedDict):
    configs: Sequence[LabelPickerConfig]
