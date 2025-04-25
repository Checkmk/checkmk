#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Callable, Mapping, Sequence

from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import ABCLabelConfig, Labels
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetMatcher,
    RuleSpec,
)
from cmk.utils.servicename import ServiceName


@dataclasses.dataclass(frozen=True)
class LabelConfig(ABCLabelConfig):
    matcher: RulesetMatcher
    host_label_rules: Sequence[RuleSpec[Mapping[str, str]]]
    service_label_rules: Sequence[RuleSpec[Mapping[str, str]]]

    def host_labels(self, host_name: HostName, /) -> Labels:
        """Returns the configured labels for a host"""
        return self.matcher.get_host_merged_dict(
            host_name,
            self.host_label_rules,
            # these cannot match on host labels, for obvious reasons
            lambda _: {},
        )

    def service_labels(
        self,
        host_name: HostName,
        service_name: ServiceName,
        labels_of_host: Callable[[HostName], Labels],
        /,
    ) -> Labels:
        """Returns the configured labels for a service"""
        return self.matcher.get_service_merged_dict(
            host_name,
            service_name,
            # these do not match on service labels
            {},
            self.service_label_rules,
            labels_of_host,
        )
