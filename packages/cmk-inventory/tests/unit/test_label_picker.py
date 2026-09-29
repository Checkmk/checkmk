#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.label_picker import (
    InventorizedHostLabelsStore,
    LabelPickerConfig,
    LabelPickerConfigAttribute,
    LabelPickerConfigCaseConversion,
    LabelPickerConfigColumn,
    LabelPickerConfigReplaceRule,
    LabelPickerConfigRowFilter,
    LabelPickerConfigRowMatch,
    LabelPickerConfigValueMatch,
    LabelPickerConfigValueMatchOrReplace,
    LabelPickerLabeling,
    LabelPickerSource,
    pick_labels,
)
from cmk.inventory.trees import (
    _MutableAttributes,
    _MutableTable,
    MutableTree,
    SDKey,
    SDNodeName,
    SDRowIdent,
    SDValue,
)

_NO_CONVERSION = LabelPickerConfigCaseConversion(label="no_conversion", value="no_conversion")


def _config(
    *,
    path: str = "hardware.os",
    label_prefix: str = "cmk/inventory",
    case_conversion: LabelPickerConfigCaseConversion = _NO_CONVERSION,
    attributes: Sequence[LabelPickerConfigAttribute] = (),
    columns: Sequence[LabelPickerConfigColumn] = (),
) -> LabelPickerConfig:
    return LabelPickerConfig(
        source=LabelPickerSource(
            path=path,
            attributes=list(attributes),
            columns=list(columns),
        ),
        labeling=LabelPickerLabeling(
            label_prefix=label_prefix,
            case_conversion=case_conversion,
        ),
    )


def _tree_with_attributes(pairs: Mapping[SDKey, SDValue]) -> MutableTree:
    return MutableTree(
        path=(),
        nodes_by_name={
            SDNodeName("hardware"): MutableTree(
                path=(SDNodeName("hardware"),),
                nodes_by_name={
                    SDNodeName("os"): MutableTree(
                        path=(SDNodeName("hardware"), SDNodeName("os")),
                        attributes=_MutableAttributes(pairs=dict(pairs)),
                    ),
                },
            ),
        },
    )


def _tree_with_table(rows_by_ident: Mapping[SDRowIdent, dict[SDKey, SDValue]]) -> MutableTree:
    return MutableTree(
        path=(),
        nodes_by_name={
            SDNodeName("hardware"): MutableTree(
                path=(SDNodeName("hardware"),),
                nodes_by_name={
                    SDNodeName("os"): MutableTree(
                        path=(SDNodeName("hardware"), SDNodeName("os")),
                        table=_MutableTable(
                            key_columns=[SDKey("name")],
                            rows_by_ident=dict(rows_by_ident),
                        ),
                    ),
                },
            ),
        },
    )


@pytest.mark.parametrize(
    "attribute, result",
    [
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=("use_value", None),
            ),
            {"cmk/inventory/label-name": "value"},
            id="use_value",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "use_value_if_matches",
                    LabelPickerConfigValueMatch(value_match="v.*"),
                ),
            ),
            {"cmk/inventory/label-name": "value"},
            id="use_value_if_matches",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "use_value_if_matches",
                    LabelPickerConfigValueMatch(value_match="nope"),
                ),
            ),
            {},
            id="use_value_if_matches-no-match",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "match_and_replace_value",
                    [LabelPickerConfigReplaceRule(value_match="v.*", value_replacement="VALUE")],
                ),
            ),
            {"cmk/inventory/label-name": "VALUE"},
            id="match_and_replace-single",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "match_and_replace_value",
                    [LabelPickerConfigReplaceRule(value_match="v(.*)", value_replacement=r"V\1")],
                ),
            ),
            {"cmk/inventory/label-name": "Value"},
            id="match_and_replace-group",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "match_and_replace_value",
                    [LabelPickerConfigReplaceRule(value_match="al", value_replacement="AL")],
                ),
            ),
            {"cmk/inventory/label-name": "AL"},
            id="match_and_replace-replaces-whole-value",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "match_and_replace_value",
                    [
                        LabelPickerConfigReplaceRule(value_match="nope", value_replacement="NOPE"),
                        LabelPickerConfigReplaceRule(
                            value_match="val.*", value_replacement="SECOND"
                        ),
                    ],
                ),
            ),
            {"cmk/inventory/label-name": "SECOND"},
            id="match_and_replace-first-matching-rule-wins",
        ),
        pytest.param(
            LabelPickerConfigAttribute(
                label_name="label-name",
                key_match="key",
                value_match=(
                    "match_and_replace_value",
                    [LabelPickerConfigReplaceRule(value_match="nope", value_replacement="NOPE")],
                ),
            ),
            {},
            id="match_and_replace-no-rule-matches-drops-value",
        ),
    ],
)
def test_pick_labels_from_attributes(
    attribute: LabelPickerConfigAttribute, result: Mapping[str, str]
) -> None:
    assert (
        pick_labels(
            _tree_with_attributes({SDKey("key"): "value"}),
            [_config(attributes=[attribute])],
        )
        == result
    )


def test_pick_labels_from_table_first_row_wins() -> None:
    assert pick_labels(
        _tree_with_table(
            {
                ("value2",): {SDKey("name"): "value2"},
                ("value1",): {SDKey("name"): "value1"},
            }
        ),
        [
            _config(
                columns=[
                    LabelPickerConfigColumn(
                        label_name="label-name",
                        column="name",
                        row_filter=("all_rows", None),
                        value_match=("use_value", None),
                    )
                ]
            )
        ],
    ) == {"cmk/inventory/label-name": "value2"}


def test_pick_labels_from_table_cross_column_with_row_filter() -> None:
    assert pick_labels(
        _tree_with_table(
            {
                ("apache2",): {SDKey("name"): "apache2", SDKey("version"): "2.4"},
                ("nginx",): {SDKey("name"): "nginx", SDKey("version"): "1.18"},
            }
        ),
        [
            _config(
                columns=[
                    LabelPickerConfigColumn(
                        label_name="webserver-version",
                        column="version",
                        row_filter=(
                            "matching_rows",
                            LabelPickerConfigRowMatch(column="name", value_match="apache"),
                        ),
                        value_match=("use_value", None),
                    )
                ]
            )
        ],
    ) == {"cmk/inventory/webserver-version": "2.4"}


def test_pick_labels_configurable_prefix() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): "value"}),
        [
            _config(
                label_prefix="my-prefix",
                attributes=[
                    LabelPickerConfigAttribute(
                        label_name="label-name",
                        key_match="key",
                        value_match=("use_value", None),
                    )
                ],
            )
        ],
    ) == {"my-prefix/label-name": "value"}


def test_pick_labels_empty_prefix_has_no_leading_slash() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): "value"}),
        [
            _config(
                label_prefix="",
                attributes=[
                    LabelPickerConfigAttribute(
                        label_name="label-name",
                        key_match="key",
                        value_match=("use_value", None),
                    )
                ],
            )
        ],
    ) == {"label-name": "value"}


def test_pick_labels_case_conversion() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): "MixedCase"}),
        [
            _config(
                case_conversion=LabelPickerConfigCaseConversion(label="upper", value="lower"),
                attributes=[
                    LabelPickerConfigAttribute(
                        label_name="Label-Name",
                        key_match="key",
                        value_match=("use_value", None),
                    )
                ],
            )
        ],
    ) == {"cmk/inventory/LABEL-NAME": "mixedcase"}


def _attribute(
    *,
    key_match: str = "key",
    label_name: str = "label-name",
    value_match: LabelPickerConfigValueMatchOrReplace = ("use_value", None),
) -> LabelPickerConfigAttribute:
    return LabelPickerConfigAttribute(
        label_name=label_name, key_match=key_match, value_match=value_match
    )


def _column(
    *,
    column: str = "version",
    row_filter: LabelPickerConfigRowFilter = ("all_rows", None),
) -> LabelPickerConfigColumn:
    return LabelPickerConfigColumn(
        label_name="label-name",
        column=column,
        row_filter=row_filter,
        value_match=("use_value", None),
    )


def test_pick_labels_from_missing_node() -> None:
    assert (
        pick_labels(
            _tree_with_attributes({SDKey("key"): "value"}),
            [_config(path="hardware.cpu", attributes=[_attribute()])],
        )
        == {}
    )


@pytest.mark.parametrize(
    "pairs",
    [
        pytest.param({}, id="missing-key"),
        pytest.param({SDKey("key"): None}, id="none"),
        pytest.param({SDKey("key"): ""}, id="empty"),
    ],
)
def test_pick_labels_from_single_value_without_value(pairs: Mapping[SDKey, SDValue]) -> None:
    assert pick_labels(_tree_with_attributes(pairs), [_config(attributes=[_attribute()])]) == {}


@pytest.mark.parametrize(
    "value, expression, label_value",
    [
        pytest.param(True, "^True$", "True", id="bool"),
        pytest.param(1.5, "^1\\.5$", "1.5", id="float"),
        pytest.param(1073741824, "^1073741824$", "1073741824", id="int"),
    ],
)
def test_pick_labels_matches_the_raw_value_as_text(
    value: SDValue, expression: str, label_value: str
) -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): value}),
        [
            _config(
                attributes=[
                    _attribute(
                        value_match=(
                            "use_value_if_matches",
                            LabelPickerConfigValueMatch(value_match=expression),
                        )
                    )
                ]
            )
        ],
    ) == {"cmk/inventory/label-name": label_value}


def test_pick_labels_converts_the_case_after_matching() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): "Apache2"}),
        [
            _config(
                case_conversion=LabelPickerConfigCaseConversion(label="lower", value="lower"),
                attributes=[
                    _attribute(
                        label_name="Web-Server",
                        value_match=(
                            "use_value_if_matches",
                            LabelPickerConfigValueMatch(value_match="^Apache"),
                        ),
                    )
                ],
            )
        ],
    ) == {"cmk/inventory/web-server": "apache2"}


def test_pick_labels_converts_the_value_to_uppercase() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("key"): "value"}),
        [
            _config(
                case_conversion=LabelPickerConfigCaseConversion(
                    label="no_conversion", value="upper"
                ),
                attributes=[_attribute()],
            )
        ],
    ) == {"cmk/inventory/label-name": "VALUE"}


def test_pick_labels_drops_an_empty_replacement() -> None:
    assert (
        pick_labels(
            _tree_with_attributes({SDKey("key"): "value"}),
            [
                _config(
                    attributes=[
                        _attribute(
                            value_match=(
                                "match_and_replace_value",
                                [
                                    LabelPickerConfigReplaceRule(
                                        value_match="value", value_replacement=""
                                    )
                                ],
                            )
                        )
                    ]
                )
            ],
        )
        == {}
    )


def test_pick_labels_from_table_skips_rows_without_the_column() -> None:
    assert pick_labels(
        _tree_with_table(
            {
                ("apache2",): {SDKey("name"): "apache2"},
                ("nginx",): {SDKey("name"): "nginx", SDKey("version"): "1.18"},
            }
        ),
        [_config(columns=[_column()])],
    ) == {"cmk/inventory/label-name": "1.18"}


def test_pick_labels_row_selection_skips_rows_without_the_filter_column() -> None:
    assert pick_labels(
        _tree_with_table(
            {
                ("apache2",): {SDKey("name"): "apache2", SDKey("version"): "2.4"},
                ("nginx",): {
                    SDKey("name"): "nginx",
                    SDKey("vendor"): "F5",
                    SDKey("version"): "1.18",
                },
            }
        ),
        [
            _config(
                columns=[
                    _column(
                        row_filter=(
                            "matching_rows",
                            LabelPickerConfigRowMatch(column="vendor", value_match=".*"),
                        )
                    )
                ]
            )
        ],
    ) == {"cmk/inventory/label-name": "1.18"}


def test_pick_labels_first_configuration_wins_for_the_same_label_name() -> None:
    assert pick_labels(
        _tree_with_attributes({SDKey("first"): "1", SDKey("second"): "2"}),
        [
            _config(attributes=[_attribute(key_match="first")]),
            _config(attributes=[_attribute(key_match="second")]),
        ],
    ) == {"cmk/inventory/label-name": "1"}


def test_pick_labels_combines_configurations_of_different_paths() -> None:
    assert pick_labels(
        MutableTree(
            path=(),
            nodes_by_name={
                SDNodeName("hardware"): MutableTree(
                    path=(SDNodeName("hardware"),),
                    attributes=_MutableAttributes(pairs={SDKey("key"): "hardware"}),
                ),
                SDNodeName("software"): MutableTree(
                    path=(SDNodeName("software"),),
                    attributes=_MutableAttributes(pairs={SDKey("key"): "software"}),
                ),
            },
        ),
        [
            _config(path="hardware", attributes=[_attribute(label_name="hw")]),
            _config(path="software", attributes=[_attribute(label_name="sw")]),
        ],
    ) == {"cmk/inventory/hw": "hardware", "cmk/inventory/sw": "software"}


def test_pick_labels_from_single_values_and_table_columns_of_one_node() -> None:
    assert pick_labels(
        MutableTree(
            path=(),
            nodes_by_name={
                SDNodeName("software"): MutableTree(
                    path=(SDNodeName("software"),),
                    attributes=_MutableAttributes(pairs={SDKey("key"): "value"}),
                    table=_MutableTable(
                        key_columns=[SDKey("name")],
                        rows_by_ident={
                            ("nginx",): {SDKey("name"): "nginx", SDKey("version"): "1.18"}
                        },
                    ),
                ),
            },
        ),
        [
            _config(
                path="software",
                attributes=[_attribute(label_name="single")],
                columns=[_column()],
            )
        ],
    ) == {"cmk/inventory/single": "value", "cmk/inventory/label-name": "1.18"}


def test_inventorized_host_labels_store_load_default(tmp_path: Path) -> None:
    assert InventorizedHostLabelsStore(HostName("host"), tmp_path).load() == {}


def test_inventorized_host_labels_store_save_load_roundtrip(tmp_path: Path) -> None:
    InventorizedHostLabelsStore(HostName("host"), tmp_path).save({"cmk/inventory/product": "foo"})
    assert InventorizedHostLabelsStore(HostName("host"), tmp_path).load() == {
        "cmk/inventory/product": "foo"
    }
