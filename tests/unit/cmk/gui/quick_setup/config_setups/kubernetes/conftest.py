#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.version import Edition
from cmk.gui.quick_setup.config_setups.kubernetes.settings import ADVANCED, CLUSTER, HOST
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.rule_specs.loader import LoadedRuleSpec
from cmk.gui.rule_specs.registering import register_plugin
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry
from cmk.plugins.kube.rulesets.special_agent_kube_v2 import rule_spec_special_agent_kube_v2
from tests.testlib.common.utils import reset_registries


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


@pytest.fixture(name="kube_v2_ruleset")
def fixture_kube_v2_ruleset() -> Iterator[None]:
    """The ruleset the Kubernetes Quick Setup saves its rule to

    The GUI finds it by plug-in discovery in production.
    """
    with reset_registries([rulespec_registry]), reset_registries([rulespec_group_registry]):
        register_plugin(
            rulespec_registry,
            LoadedRuleSpec(
                rule_spec=rule_spec_special_agent_kube_v2, edition_only=Edition.COMMUNITY
            ),
        )
        yield
