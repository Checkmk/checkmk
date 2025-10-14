#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator

from cmk.agent_based.v2 import TableRow
from cmk.plugins.kube.schemata.api import Labels, MatchExpressions, MatchLabels


def match_labels_to_str(match_labels: MatchLabels) -> str:
    """Creates expression, which can be parsed by kubectl"""

    return ", ".join(f"{label_name}={label_key}" for label_name, label_key in match_labels.items())


def match_expressions_to_str(match_expressions: MatchExpressions) -> str:
    """Creates expression, which can be parsed by kubectl"""
    pretty_match_expressions: list[str] = []
    for match_expression in match_expressions:
        key, operator = match_expression.key, match_expression.operator
        if operator == "Exists":
            pretty_match_expressions.append(key)
        elif operator == "DoesNotExist":
            pretty_match_expressions.append(f"!{key}")
        elif operator in ("In", "NotIn"):
            pretty_values = ", ".join(match_expression.values)
            pretty_match_expressions.append(f"{key} {operator.lower()} ({pretty_values})")
        else:
            raise AssertionError("Unknown operator in match expression")
    return ", ".join(pretty_match_expressions)


def labels_to_table(labels: Labels) -> Iterator[TableRow]:
    """Populate table of labels.

    This function is intended for usage with HW/SW Inventory on a Kubernetes objects. It picks the
    correct path, and relies on the uniqueness of the label names of a Kubernetes objects. Using
    this function ensures a uniform look across inventories.

        Typical usage example:

        yield from labels_to_table(section_info.labels)
    """

    for label in labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )
