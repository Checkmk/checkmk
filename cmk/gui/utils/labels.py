#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Literal, NamedTuple

from livestatus import LivestatusResponse, lqencode, quote_dict

from cmk.ccc.site import SiteId

from cmk.utils.labels import AndOrNotLiteral, LabelGroups, single_label_group_from_labels

from cmk.gui import sites
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import FilterHTTPVariables


class Label(NamedTuple):
    id: str
    value: str
    negate: bool


class LabelType(enum.StrEnum):
    HOST = "host"
    SERVICE = "service"
    ALL = "all"


Labels = Iterable[Label]

# Labels need to be in the format "<key>:<value>", e.g. "os:windows"
LABEL_REGEX = r"^[^:]+:[^:]+$"


class _LivestatusLabelResponse(NamedTuple):
    host_rows: LivestatusResponse
    service_rows: LivestatusResponse


class _MergedLabels(NamedTuple):
    hosts: dict[SiteId, dict[str, str]]
    services: dict[SiteId, dict[str, str]]


def parse_labels_value(value: str) -> Labels:
    try:
        decoded_labels = json.loads(value or "[]")
    except ValueError as e:
        raise MKUserError(None, _("Failed to parse labels: %s") % e)

    seen: set[str] = set()
    for entry in decoded_labels:
        label_id, label_value = (p.strip() for p in entry["value"].split(":", 1))
        if label_id in seen:
            raise MKUserError(
                None,
                _('A label key can be used only once per object. The Label key "%s" is used twice.')
                % label_id,
            )
        yield Label(label_id, label_value, False)
        seen.add(label_id)


def encode_label_for_livestatus(column: str, label: Label) -> str:
    """
    >>> encode_label_for_livestatus("labels", Label("key", "value", False))
    "Filter: labels = 'key' 'value'"
    """
    return "Filter: {} {} {} {}".format(
        lqencode(column),
        "!=" if label.negate else "=",
        lqencode(quote_dict(label.id)),
        lqencode(quote_dict(label.value)),
    )


def encode_labels_for_livestatus(
    column: str,
    labels: Labels,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", [Label("key", "value", False), Label("x", "y", False)])
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'\\n"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    if headers := "\n".join(encode_label_for_livestatus(column, label) for label in labels):
        return headers + "\n"
    return ""


def encode_label_groups_for_livestatus(
    column: str,
    label_groups: LabelGroups,
) -> str:
    """Apply the boolean standard prioritization of operators, i.e. NOT, AND, OR. Filter strings
    for OR operators are added at the end of a group for label lvl ORs, and at the end of the entire
    query for group lvl ORs.
    >>> encode_label_groups_for_livestatus("host_labels", [])
    ''
    >>> encode_label_groups_for_livestatus("host_labels", [("and", [("and", "label:a"), ("or", "label:b"), ("and", "even:true")])])
    "Filter: host_labels = 'label' 'a'\\nFilter: host_labels = 'label' 'b'\\nFilter: host_labels = 'even' 'true'\\nAnd: 2\\nOr: 2\\n"
    >>> encode_label_groups_for_livestatus("host_labels", [("and", [("not", "label:a")]), ("or", [("and", "label:b")]), ("not", [("and", "label:c")])])
    "Filter: host_labels = 'label' 'a'\\nNegate:\\nFilter: host_labels = 'label' 'b'\\nFilter: host_labels = 'label' 'c'\\nNegate:\\nAnd: 2\\nOr: 2\\n"
    """
    filter_str: str = ""
    group_lvl_or_operators_str: str = ""
    is_first_group: bool = True
    group_operator: AndOrNotLiteral

    for group_operator, label_group in label_groups:
        label_lvl_or_operators_str: str = ""
        is_first_label: bool = True
        label_operator: AndOrNotLiteral

        for label_operator, label in label_group:
            if not label:
                continue

            label_id, label_val = label.split(":")
            filter_str += (
                encode_label_for_livestatus(column, Label(label_id, label_val, False)) + "\n"
            )
            if label_operator == "or":
                label_lvl_or_operators_str += _operator_filter_str(label_operator, is_first_label)
            else:
                filter_str += _operator_filter_str(label_operator, is_first_label)
            is_first_label = False

        filter_str += label_lvl_or_operators_str

        if not is_first_label:  # The current group holds at least one non empty label
            if group_operator == "or":
                group_lvl_or_operators_str += _operator_filter_str(group_operator, is_first_group)
            else:
                filter_str += _operator_filter_str(group_operator, is_first_group)
            is_first_group = False

    return filter_str + group_lvl_or_operators_str


# Type of argument operator should be 'Operator'
def _operator_filter_str(operator: AndOrNotLiteral, is_first: bool) -> str:
    if is_first:
        if operator == "not":
            # Negate without And for the first element
            return "Negate:\n"
        # No filter str for and/or for the first element
        return ""
    if operator == "not":
        # Negate with And for non-first elements
        return "Negate:\nAnd: 2\n"
    # "And: 2\n" or "Or: 2\n"
    return f"{operator.title()}: 2\n"


def encode_labels_for_tagify(
    labels: Labels | Iterable[tuple[str, str]],
) -> Iterable[Mapping[str, str]]:
    """
    >>> encode_labels_for_tagify({"key": "value", "x": "y"}.items()) ==  encode_labels_for_tagify([Label("key", "value", False), Label("x", "y", False)])
    True
    """
    return [{"value": "%s:%s" % e[:2]} for e in labels]


def encode_labels_for_http(labels: Labels | Iterable[tuple[str, str]]) -> str:
    """The result can be used in building URLs
    >>> encode_labels_for_http([])
    '[]'
    >>> encode_labels_for_http({"key": "value", "x": "y"}.items())
    '[{"value": "key:value"}, {"value": "x:y"}]'
    """
    return json.dumps(encode_labels_for_tagify(labels))


def label_help_text() -> str:
    return _(
        "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>cmk/os_family:linux</tt>."
    )


def get_labels_from_config(label_type: LabelType, search_label: str) -> Sequence[tuple[str, str]]:
    # TODO: Until we have a config specific implementation we now use the labels known to the
    # core. This is not optimal, but better than doing nothing.
    # To implement a setup specific search, we need to decide which occurrences of labels we
    # want to search: hosts / folders, rules, ...?
    return get_labels_from_core(label_type, search_label)


def get_labels_from_core(
    label_type: LabelType, search_label: str | None = None
) -> Sequence[tuple[str, str]]:
    all_labels = _get_labels_from_livestatus(label_type)
    if search_label is None:
        return list(all_labels)
    return [
        (ident, value) for ident, value in all_labels if search_label in ":".join([ident, value])
    ]


def _get_labels_from_livestatus(
    label_type: LabelType,
) -> set[tuple[str, str]]:
    if label_type == LabelType.HOST:
        query = "GET hosts\nCache: reload\nColumns: labels\n"
    elif label_type == LabelType.SERVICE:
        query = "GET services\nCache: reload\nColumns: labels\n"
    elif label_type == LabelType.ALL:
        query = "GET labels\nCache: reload\nColumns: name value\n"
    else:
        raise ValueError("Unsupported livestatus query")

    try:
        sites.live().set_auth_domain("labels")
        with sites.only_sites(list(user.authorized_sites().keys())):
            label_rows = sites.live().query(query)
    finally:
        sites.live().set_auth_domain("read")

    if label_type == LabelType.ALL:
        return {(str(label[0]), str(label[1])) for label in label_rows}

    return {(k, v) for row in label_rows for labels in row for k, v in labels.items()}


def _parse_label_groups_to_http_vars(
    label_groups: LabelGroups, object_type: Literal["host", "service"]
) -> FilterHTTPVariables:
    prefix: str = f"{object_type}_labels"  # "[host|service]_labels"
    filter_vars: dict[str, str] = {
        f"{prefix}_count": "%d" % len(label_groups),
    }
    for i, (group_operator, group) in enumerate(label_groups, 1):
        filter_vars.update(
            {
                f"{prefix}_{i}_vs_count": "%d" % len(group),
                f"{prefix}_{i}_bool": group_operator,
                f"{prefix}_indexof_{i}": str(i),
            }
        )

        for j, (label_operator, label) in enumerate(group, 1):
            filter_vars.update(
                {
                    f"{prefix}_{i}_vs_{j}_bool": label_operator,
                    f"{prefix}_{i}_vs_{j}_vs": label,
                    f"{prefix}_{i}_vs_indexof_{j}": str(j),
                }
            )

    return filter_vars


def filter_http_vars_for_simple_label_group(
    labels: Sequence[str],
    object_type: Literal["host", "service"],
    operator: AndOrNotLiteral = "and",
) -> FilterHTTPVariables:
    """Return HTTP vars for one label group of type <object_type>, containing all <labels> and
    connecting all of them by the same logical <operator>.

    >>> filter_http_vars_for_simple_label_group(["foo:bar", "check:mk"], "host")
    {'host_labels_count': '1', 'host_labels_1_vs_count': '2', 'host_labels_1_bool': 'and', 'host_labels_indexof_1': '1', 'host_labels_1_vs_1_bool': 'and', 'host_labels_1_vs_1_vs': 'foo:bar', 'host_labels_1_vs_indexof_1': '1', 'host_labels_1_vs_2_bool': 'and', 'host_labels_1_vs_2_vs': 'check:mk', 'host_labels_1_vs_indexof_2': '2'}
    """
    return _parse_label_groups_to_http_vars(
        single_label_group_from_labels(labels, operator),
        object_type,
    )


def parse_label_groups_from_http_vars(prefix: str, value: FilterHTTPVariables) -> LabelGroups:
    label_groups: list = []
    groups_count: int = _get_validated_count_value(f"{prefix}_count", value)
    labels_count: int
    for i in range(1, groups_count + 1):
        labels_count = _get_validated_count_value(f"{prefix}_{i}_vs_count", value)
        label_group_operator: str = _get_validated_operator_value(f"{prefix}_{i}_bool", value)
        label_group = []
        for j in range(1, labels_count + 1):
            operator: str = _get_validated_operator_value(f"{prefix}_{i}_vs_{j}_bool", value)
            if vs_value := value.get(f"{prefix}_{i}_vs_{j}_vs"):
                label_group.append((operator, vs_value))

        if label_group:
            label_groups.append((label_group_operator, label_group))

    return label_groups


def _get_validated_count_value(ident: str, value: FilterHTTPVariables) -> int:
    try:
        str_val: str = value.get(ident) or "0"
        return int(str_val)
    except ValueError:
        raise MKUserError(
            ident,
            _('The value "%s" of HTTP variable "%s" is not an integer.') % (str_val, ident),
        )


def _get_validated_operator_value(ident: str, value: FilterHTTPVariables) -> str:
    operator: str = value.get(ident, "and")
    if operator not in ["and", "or", "not"]:
        raise MKUserError(
            ident,
            _(
                'The value "%s" of HTTP variable "%s" is not a valid operator ({"and", "or", "not"}).'
            )
            % (operator, ident),
        )
    return operator
