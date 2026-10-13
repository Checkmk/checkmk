#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.ccc.regex import regex

from .trees import (
    MutableTree,
    SDKey,
    SDNodeName,
    SDValue,
)

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


def _convert_case(text: str, conversion: LabelPickerCaseConversion) -> str:
    match conversion:
        case "no_conversion":
            return text
        case "lower":
            return text.lower()
        case "upper":
            return text.upper()


def _replaced_value(value: str, rules: Sequence[LabelPickerConfigReplaceRule]) -> str:
    for rule in rules:
        if value_found := regex(rule["value_match"]).search(value):
            return value_found.expand(rule["value_replacement"])
    return ""


def _compute_label_value(
    *, value_match: LabelPickerConfigValueMatchOrReplace, value: SDValue
) -> str:
    if value is None:
        return ""
    value_str = str(value)
    match value_match:
        case ("use_value", _):
            return value_str
        case ("use_value_if_matches", value_condition):
            return value_str if regex(value_condition["value_match"]).search(value_str) else ""
        case ("match_and_replace_value", rules):
            return _replaced_value(value_str, rules)


def _compute_label_name(prefix: str, label_name: str, conversion: LabelPickerCaseConversion) -> str:
    name = _convert_case(label_name, conversion)
    return f"{prefix}/{name}" if prefix else name


def _row_matches(row: Mapping[SDKey, SDValue], row_filter: LabelPickerConfigRowFilter) -> bool:
    match row_filter:
        case ("all_rows", None):
            return True
        case ("matching_rows", row_match):
            value = row.get(SDKey(row_match["column"]))
            return value is not None and bool(regex(row_match["value_match"]).search(str(value)))


def _pick_labels_of_node(node: MutableTree, config: LabelPickerConfig) -> Iterator[tuple[str, str]]:
    prefix = config["labeling"]["label_prefix"]
    case_conversion = config["labeling"]["case_conversion"]

    for attr_config in config["source"]["attributes"]:
        if label_value := _compute_label_value(
            value_match=attr_config["value_match"],
            value=node.attributes.pairs.get(SDKey(attr_config["key_match"])),
        ):
            yield (
                _compute_label_name(prefix, attr_config["label_name"], case_conversion["label"]),
                _convert_case(label_value, case_conversion["value"]),
            )

    for col_config in config["source"]["columns"]:
        for row in node.table.rows_by_ident.values():
            if _row_matches(row, col_config["row_filter"]) and (
                label_value := _compute_label_value(
                    value_match=col_config["value_match"],
                    value=row.get(SDKey(col_config["column"])),
                )
            ):
                yield (
                    _compute_label_name(prefix, col_config["label_name"], case_conversion["label"]),
                    _convert_case(label_value, case_conversion["value"]),
                )


def pick_labels(
    tree: MutableTree, label_picker_configs: Sequence[LabelPickerConfig]
) -> Mapping[str, str]:
    labels: dict[str, str] = {}
    for config in label_picker_configs:
        path = tuple(SDNodeName(e) for e in config["source"]["path"].split("."))
        if node := tree.get_tree(path):
            for name, value in _pick_labels_of_node(node, config):
                labels.setdefault(name, value)
    return labels


class _LabelsSerializer:
    def serialize(self, data: Mapping[str, str]) -> bytes:
        return json.dumps(data).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Mapping[str, str]:
        return {str(k): str(v) for k, v in json.loads(raw.decode("utf-8")).items()}


class InventorizedHostLabelsStore:
    def __init__(self, host_name: HostName, inventorized_host_labels_dir: Path) -> None:
        self._store = store.ObjectStore(
            path=inventorized_host_labels_dir / f"{host_name}.json",
            serializer=_LabelsSerializer(),
        )

    def load(self) -> Mapping[str, str]:
        return self._store.read_obj(default={})

    def save(self, labels: Mapping[str, str]) -> None:
        self._store.path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj(labels)
