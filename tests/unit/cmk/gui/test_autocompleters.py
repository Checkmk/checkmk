#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.autocompleters import autocompleter_registry


def test_builtin_autocompleters_registered() -> None:
    registered = autocompleter_registry.keys()
    expected = [
        "add_to_dashboard_choices",
        "allgroups",
        "available_graph_templates",
        "check_cmd",
        "check_types",
        "config_hostname",
        "kubernetes_labels",
        "label",
        "monitored_hostname",
        "monitored_metrics",
        "monitored_service_description",
        "service_levels",
        "sites",
        "syslog_facilities",
        "tag_groups",
        "tag_groups_opt",
        "wato_folder_choices",
    ]

    assert sorted(registered) == sorted(expected)
