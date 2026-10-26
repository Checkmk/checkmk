#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_visual_types() -> None:
    assert sorted(visual_type_registry) == [
        "dashboards",
        "views",
    ]


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_visual_infos() -> None:
    # the inventory infos are generated from the inventory_ui plugins found in the test sandbox
    assert sorted(i for i in visual_info_registry if not i.startswith("inv")) == [
        "aggr",
        "aggr_group",
        "command",
        "comment",
        "contact",
        "crash",
        "discovery",
        "downtime",
        "event",
        "history",
        "host",
        "hostgroup",
        "kubecluster",
        "kubedaemonset",
        "kubedeployment",
        "kubenamespace",
        "kubestatefulset",
        "log",
        "service",
        "servicegroup",
    ]
