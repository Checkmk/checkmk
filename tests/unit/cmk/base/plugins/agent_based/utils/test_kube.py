#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.utils.kube import (
    kube_labels_to_cmk_labels,
    Label,
    LabelName,
    Labels,
)


def test_kube_labels_to_cmk_labels() -> None:
    labels: Labels = {
        LabelName("asd"): Label(name="asd", value="bsd"),
        LabelName("empty"): Label(name="empty", value=""),
    }
    result = list(kube_labels_to_cmk_labels(labels))
    assert result == [
        HostLabel("cmk/kubernetes/label/asd", "bsd"),
        HostLabel("cmk/kubernetes/label/empty", "true"),
    ]
