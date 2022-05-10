#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from typing import Optional, Sequence

import pytest

from cmk.base.api.agent_based.checking_classes import Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from cmk.base.plugins.agent_based.utils import gcp


class ParsingTester(ABC):
    @abstractmethod
    def parse(self, string_table: StringTable) -> gcp.Section:
        pass

    @property
    @abstractmethod
    def section_table(self) -> StringTable:
        raise NotImplementedError

    def test_parse(self):
        section = self.parse(self.section_table)
        n_rows = sum(len(i.rows) for i in section.values())
        # first row contains general section information and no metrics
        assert n_rows == len(self.section_table)


class DiscoverTester(ABC):
    @property
    @abstractmethod
    def _assets(self) -> StringTable:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_services(self) -> set[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def expected_labels(self) -> set[ServiceLabel]:
        raise NotImplementedError

    @abstractmethod
    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        pass

    ###########
    # Fixture #
    ###########

    @pytest.fixture(name="asset_section")
    def fixture_asset_section(self) -> gcp.AssetSection:
        return gcp.parse_assets(self._assets)

    @pytest.fixture(name="services")
    def fixture_services(self, asset_section):
        return list(self.discover(assets=asset_section))

    #######################
    # Test implementation #
    #######################

    def test_no_assets_yield_no_section(self):
        assert len(list(self.discover(assets=None))) == 0

    def test_discover_project_label(self, services: Sequence[Service]):
        for asset in services:
            assert ServiceLabel("gcp/projectId", "backup-255820") in asset.labels

    def test_discover_all_services(self, services: Sequence[Service]):
        assert {a.item for a in services} == self.expected_services

    def test_discover_all_services_labels(self, services: Sequence[Service]):
        assert set(services[0].labels) == self.expected_labels
