#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import HostLabel
from cmk.plugins.kube.schemata.api import Label, LabelName, Labels, LabelValue
from cmk.plugins.lib.kube import kube_labels_to_cmk_labels


def test_kube_labels_to_cmk_labels() -> None:
    labels: Labels = {
        LabelName("asd"): Label(name=LabelName("asd"), value=LabelValue("bsd")),
        LabelName("empty"): Label(name=LabelName("empty"), value=LabelValue("")),
    }
    result = list(kube_labels_to_cmk_labels(labels))
    assert result == [
        HostLabel("cmk/kubernetes/label/asd", "bsd"),
        HostLabel("cmk/kubernetes/label/empty", "true"),
    ]
