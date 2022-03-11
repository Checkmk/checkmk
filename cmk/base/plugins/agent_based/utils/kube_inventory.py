#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Iterator, List

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.utils.k8s import Labels, MatchExpressions, MatchLabels


def match_labels_to_str(match_labels: MatchLabels) -> str:
    """Creates expression, which can be parsed by kubectl

    >>> from cmk.base.plugins.agent_based.utils.k8s import LabelValue, LabelName
    >>> match_labels_to_str(
    ...    {
    ...        LabelName("app"): LabelValue("agent"),
    ...        LabelName("k8s-app"): LabelValue("kube-dns"),
    ...    }
    ... )
    'app=agent, k8s-app=kube-dns'

    """

    return ", ".join(f"{label_name}={label_key}" for label_name, label_key in match_labels.items())


def match_expressions_to_str(match_expressions: MatchExpressions) -> str:
    """Creates expression, which can be parsed by kubectl

    >>> from cmk.base.plugins.agent_based.utils.k8s import LabelValue, LabelName
    >>> match_expressions_to_str(
    ...         [
    ...             {
    ...                 "key": LabelName("app"),
    ...                 "operator": "In",
    ...                 "values": [LabelValue("agent"), LabelValue("kube-dns")],
    ...             },
    ...             {
    ...                 "key": LabelName("k8s-app"),
    ...                 "operator": "Exists",
    ...                 "values": [],
    ...             },
    ...             {
    ...                 "key": LabelName("k8s"),
    ...                 "operator": "DoesNotExist",
    ...                 "values": [],
    ...             },
    ...             {
    ...                 "key": LabelName("k8s"),
    ...                 "operator": "NotIn",
    ...                 "values": [LabelValue("check")],
    ...             },
    ...         ]
    ...     )
    'app in (agent, kube-dns), k8s-app, !k8s, k8s notin (check)'

    """
    pretty_match_expressions: List[str] = []
    for match_expression in match_expressions:
        key, operator = match_expression["key"], match_expression["operator"]
        if operator == "Exists":
            pretty_match_expressions.append(key)
        elif operator == "DoesNotExist":
            pretty_match_expressions.append(f"!{key}")
        elif operator in ("In", "NotIn"):
            pretty_values = ", ".join(match_expression["values"])
            pretty_match_expressions.append(f"{key} {operator.lower()} ({pretty_values})")
        else:
            raise AssertionError("Unknown operator in match expression")
    return ", ".join(pretty_match_expressions)


def labels_to_table(labels: Labels) -> Iterator[TableRow]:
    """Populate table of labels.

    This function is intended for usage with HW/SW inventory on a Kubernetes objects. It picks the
    correct path, and relies on the uniqueness of the label names of a Kubernetes objects. Using
    this function ensures a uniform look across inventories.

        Typical usage example:

        yield from labels_to_table(section_info.labels)

    >>> from cmk.base.plugins.agent_based.utils.k8s import LabelName, Label
    >>> list(labels_to_table({LabelName("app"): Label(name="app", value="checkmk-cluster-agent")}))
    [TableRow(path=['software', 'applications', 'kube', 'labels'], key_columns={'label_name': 'app'}, inventory_columns={'label_value': 'checkmk-cluster-agent'}, status_columns={})]
    """

    for label in labels.values():
        yield TableRow(
            path=["software", "applications", "kube", "labels"],
            key_columns={"label_name": label.name},
            inventory_columns={"label_value": label.value},
        )
