#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import re
from collections.abc import Sequence
from pathlib import Path

import pytest
from pytest import CaptureFixture

from cmk.plugins.cisco_meraki.lib import agent
from cmk.plugins.cisco_meraki.lib.agent import MerakiOrganisation, MerakiRunContext
from cmk.plugins.cisco_meraki.lib.clients import MerakiClient
from cmk.plugins.cisco_meraki.lib.config import _RequiredSections, MerakiConfig
from tests.unit.cmk.plugins.cisco_meraki.lib.factories import DeviceFactory, RawOrganizationFactory

from .fakes import FakeMerakiSDK

_DEFAULT_ARGS = ["heute", "--apikey", "my-api-key"]


@pytest.fixture(autouse=True)
def patch_storage_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


class TestMerakiAgentOutput:
    @pytest.fixture
    def ctx(self) -> MerakiRunContext:
        args = agent.parse_arguments([*_DEFAULT_ARGS, "--no-cache", "--org-id-as-prefix"])
        config = MerakiConfig.build(args)
        client = MerakiClient(FakeMerakiSDK(), config)
        return MerakiRunContext(config=config, client=client)

    def test_no_errors(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)
        assert capsys.readouterr().err == ""

    def test_section_headings(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)

        # NOTE: testing on a set here because there could be duplicate matches with multiple orgs.
        value = set(re.findall(r"<<<cisco_meraki_org_(\w+):sep\(0\)>>>", capsys.readouterr().out))
        expected = {
            "api_response_codes",
            "appliance_uplinks",
            "appliance_vpns",
            "device_info",
            "device_status",
            "device_uplinks_info",
            "licenses_overview",
            "networks",
            "organisations",
            "sensor_readings",
            "wireless_ethernet_statuses",
        }

        assert value == expected

    def test_non_default_sections(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        non_default_sections = {
            "appliance-performance",
            "switch-port-statuses",
            "wireless-device-statuses",
        }
        updated_ctx = self._update_section_names(ctx, sections=non_default_sections)
        agent.run(updated_ctx)

        # NOTE: testing on a set here because there could be duplicate matches with multiple orgs.
        value = set(re.findall(r"<<<cisco_meraki_org_(\w+):sep\(0\)>>>", capsys.readouterr().out))
        expected = {
            "appliance_performance",
            "device_info",
            "networks",
            "organisations",
            "switch_port_statuses",
            "wireless_device_statuses",
        }

        assert value == expected

    def test_piggyback_headings(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)

        value = set(re.findall(r"<<<<(\w+-\w+)>>>>", capsys.readouterr().out))
        # prefixed with org ID
        expected = {
            "123-dev1",
            "123-dev2",
            "123-sw1",
            "123-wes1",
            "456-dev3",
            "456-sw2",
            "456-wes2",
        }

        assert value == expected

    # TODO: reevaluate this test. It's a bit clunky because some sections are always written.
    def test_section_specified(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        updated_ctx = self._update_section_names(ctx, sections={"licenses-overview"})
        agent.run(updated_ctx)

        value = re.findall(r"<<<cisco_meraki_org_(\w+):sep\(0\)>>>", capsys.readouterr().out)
        expected = ["organisations", "licenses_overview", "networks"]

        assert value == expected

    def test_section_specified_size(
        self, ctx: MerakiRunContext, capsys: CaptureFixture[str]
    ) -> None:
        agent.run(ctx)
        agent_output_all_orgs = capsys.readouterr().out

        updated_ctx = self._update_section_names(ctx, sections={"licenses-overview"})
        agent.run(updated_ctx)
        agent_output_with_org = capsys.readouterr().out

        assert len(agent_output_all_orgs) > len(agent_output_with_org)

    def test_unknown_org(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        updated_ctx = self._update_org_ids(ctx, org_ids=["made-up-org"])
        agent.run(updated_ctx)
        assert capsys.readouterr().out == ""

    def test_org_specified_size(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)
        agent_output_all_orgs = capsys.readouterr().out

        updated_ctx = self._update_org_ids(ctx, org_ids=["123"])
        agent.run(updated_ctx)
        agent_output_with_org = capsys.readouterr().out

        assert len(agent_output_all_orgs) > len(agent_output_with_org)

    @pytest.mark.usefixtures("patch_storage_env")
    def test_cache_is_being_used(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        only_cached_sections = ["--sections", "device-statuses", "licenses-overview"]
        args = agent.parse_arguments([*_DEFAULT_ARGS, *only_cached_sections])
        config = MerakiConfig.build(args)
        client = MerakiClient(FakeMerakiSDK(), config)
        ctx = MerakiRunContext(config=config, client=client)

        agent.run(ctx)
        first_run = capsys.readouterr().out
        agent.run(ctx)
        second_run = capsys.readouterr().out

        assert first_run == second_run

    def _update_org_ids(self, ctx: MerakiRunContext, org_ids: Sequence[str]) -> MerakiRunContext:
        patched_config = dataclasses.replace(ctx.config, org_ids=org_ids)
        return dataclasses.replace(ctx, config=patched_config)

    def _update_section_names(self, ctx: MerakiRunContext, sections: set[str]) -> MerakiRunContext:
        patched_required = _RequiredSections.build(sections=sections)
        patched_config = dataclasses.replace(ctx.config, required=patched_required)
        return dataclasses.replace(ctx, config=patched_config)


class TestMerakiOrganizationPiggybackDevice:
    @pytest.fixture
    def meraki_org(self) -> MerakiOrganisation:
        config = MerakiConfig.build(agent.parse_arguments(_DEFAULT_ARGS))
        client = MerakiClient(FakeMerakiSDK(), config)
        org = RawOrganizationFactory.build(id="123", name="Org-123")
        return MerakiOrganisation(config=config, client=client, organisation=org)

    def test_device_not_found(self, meraki_org: MerakiOrganisation) -> None:
        assert meraki_org._get_device_piggyback(serial="xyz", devices_by_serial={}) is None

    def test_device_name_available(self, meraki_org: MerakiOrganisation) -> None:
        devices_by_serial = {"xyz": DeviceFactory.build(name="dev1")}
        assert meraki_org._get_device_piggyback("xyz", devices_by_serial) == "dev1"

        value = meraki_org._get_device_piggyback("xyz", devices_by_serial)
        expected = "dev1"

        assert value == expected

    def test_with_org_id_prefix_configured(self, meraki_org: MerakiOrganisation) -> None:
        meraki_org = self._enable_org_id_as_prefix(meraki_org)
        devices_by_serial = {"xyz": DeviceFactory.build(organization_id="123", name="dev1")}

        value = meraki_org._get_device_piggyback("xyz", devices_by_serial)
        expected = "123-dev1"

        assert value == expected

    def _enable_org_id_as_prefix(self, meraki_org: MerakiOrganisation) -> MerakiOrganisation:
        patched_config = dataclasses.replace(meraki_org.config, org_id_as_prefix=True)
        return dataclasses.replace(meraki_org, config=patched_config)
