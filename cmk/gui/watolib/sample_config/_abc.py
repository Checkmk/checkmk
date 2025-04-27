#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.groups import AllGroupSpecs, GroupName, GroupSpec
from cmk.gui.watolib.config_domain_name import SampleConfigGenerator
from cmk.gui.watolib.groups_io import save_group_information


class SampleConfigGeneratorABCGroups(SampleConfigGenerator):
    @classmethod
    def ident(cls) -> str:
        return "contact_groups"

    @classmethod
    def sort_index(cls) -> int:
        return 10

    @abc.abstractmethod
    def _all_group_spec(self) -> GroupSpec:
        raise NotImplementedError()

    def generate(self) -> None:
        # A contact group for all hosts and services
        groups: AllGroupSpecs = {"contact": {GroupName("all"): self._all_group_spec()}}
        save_group_information(groups, pprint_value=True)
