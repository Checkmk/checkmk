#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import TypeAdapter

from cmk.gui.monitor.legacy_context import PageFilterModel
from cmk.gui.type_defs import FilterHTTPVariables

# A page that accepts any tree, so that tests see the translation unchanged.
ANY_PAGE = PageFilterModel(tree=TypeAdapter(dict[str, object]), check=lambda tree: tree)

# Groups of (operator, label) pairs, each group with the operator that joins it to the ones before.
type LabelGroups = list[tuple[str, list[tuple[str, str]]]]


def label_group_variables(groups: LabelGroups) -> FilterHTTPVariables:
    """The variables the legacy form sends for the host label filter.

    The legacy form builds each entry of a list from an operator and a value, which it names
    "<prefix>_bool" and "<prefix>_vs" ("vs" for valuespec). A group is such an entry, and so is each
    label in it. The value of a group is the list of its labels, which is why its variables start
    with "<group>_vs". For two groups of labels, the second with two labels:

        host_labels_count        = "2"      number of groups
        host_labels_1_bool       = "and"    operator of group 1
        host_labels_1_vs_count   = "1"      number of labels in group 1
        host_labels_1_vs_1_bool  = "and"    operator of label 1 in group 1
        host_labels_1_vs_1_vs    = "a:1"    label 1 in group 1
        host_labels_2_bool       = "or"
        host_labels_2_vs_count   = "2"
        host_labels_2_vs_1_bool  = "and"
        host_labels_2_vs_1_vs    = "b:1"
        host_labels_2_vs_2_bool  = "not"
        host_labels_2_vs_2_vs    = "c:1"

    The form also sends "<prefix>_indexof_<n>" variables to keep the order of the entries, which
    nobody reads on the server.
    """
    variables = {"host_labels_count": str(len(groups))}
    for number, (group_operator, labels) in enumerate(groups, 1):
        variables[f"host_labels_{number}_vs_count"] = str(len(labels))
        variables[f"host_labels_{number}_bool"] = group_operator
        for label_number, (operator, label) in enumerate(labels, 1):
            variables[f"host_labels_{number}_vs_{label_number}_bool"] = operator
            variables[f"host_labels_{number}_vs_{label_number}_vs"] = label
    return variables
