#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import cmk.utils.paths
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.core.nagios._create_config import NagiosCoreConfig
from cmk.ruleset_matcher.labels import ABCLabelConfig, LabelManager, Labels
from cmk.ruleset_matcher.matcher import RulesetMatcher

EMPTY_CONFIG = BaseConfig()


EMPTY_NAGIOS_CORE_CONFIG = NagiosCoreConfig(
    delay_precompile=False,
    host_template="check_mk_host",
    cluster_template="check_mk_cluster",
    pingonly_template="check_mk_pingonly",
    active_service_template="check_mk_active",
    passive_service_template_perf="check_mk_passive_perf",
    inventory_check_template="check_mk_inventory",
    service_dependency_template="check_mk",
    generate_hostconf=True,
    generate_dummy_commands=True,
    dummy_check_commandline=(
        'echo "ERROR - you did an active check on this service - please disable active checks" '
        "&& exit 1"
    ),
    default_host_group="check_mk",
    extra_nagios_conf="",
    contacts={},
    define_contactgroups={},
    define_hostgroups={},
    define_servicegroups={},
    contactgroup_members={},
    simulation_mode=False,
)


class EmptyLabelConfig(ABCLabelConfig):
    @override
    def host_labels(self, hn: object) -> Labels:
        return {}

    @override
    def service_labels(self, hn: object, sd: object, sn: object) -> Labels:
        return {}


def make_trivial_label_manager() -> LabelManager:
    return LabelManager(
        EmptyLabelConfig(),
        {},
        {},
        builtin_host_labels_file=cmk.utils.paths.builtin_host_labels_file,
        discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
    )


def make_trivial_ruleset_matcher() -> RulesetMatcher:
    return RulesetMatcher({}, {}, frozenset(), {}, {})
