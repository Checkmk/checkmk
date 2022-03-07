#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import List

from cmk.base.plugins.agent_based.utils.k8s import MatchExpressions, MatchLabels


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
