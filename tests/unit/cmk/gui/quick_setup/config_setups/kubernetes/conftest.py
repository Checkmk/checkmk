#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.quick_setup.config_setups.kubernetes.settings import ADVANCED, CLUSTER, HOST
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId


@pytest.fixture
def data() -> ParsedFormData:
    return {
        FormSpecId("formspec_unique_id"): {"bundle_id": "kubernetes_config_1"},
        CLUSTER: {
            "cluster_name": "production",
            "namespace": "monitoring",
            "host_kinds": ["nodes"],
            "namespaces": ("exclude", ["^test"]),
        },
        ADVANCED: {"excluded_node_roles": [], "annotations": ("pattern", "^example")},
        HOST: {"host_name_source": ("cluster_name", None), "host_path": ""},
    }
