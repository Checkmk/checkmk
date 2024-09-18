#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._legacy import AutomaticDict


def test_automatic_dict_append() -> None:
    automatic_dict = AutomaticDict(list_identifier="appended")
    automatic_dict["graph_1"] = {
        "metrics": [
            ("some_metric", "line"),
            ("some_other_metric", "-area"),
        ],
    }
    automatic_dict["graph_2"] = {
        "metrics": [
            ("something", "line"),
        ],
    }
    automatic_dict.append(
        {
            "metrics": [
                ("abc", "line"),
            ],
        }
    )
    automatic_dict.append(
        {
            "metrics": [
                ("xyz", "line"),
            ],
        }
    )
    automatic_dict.append(
        {
            "metrics": [
                ("xyz", "line"),
            ],
        }
    )
    assert dict(automatic_dict) == {
        "appended_0": {
            "metrics": [("abc", "line")],
        },
        "appended_1": {
            "metrics": [("xyz", "line")],
        },
        "graph_1": {
            "metrics": [
                ("some_metric", "line"),
                ("some_other_metric", "-area"),
            ],
        },
        "graph_2": {
            "metrics": [("something", "line")],
        },
    }
