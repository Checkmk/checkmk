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
from cmk.plugins.cisco_meraki.lib.agent import MerakiRunContext
from cmk.plugins.cisco_meraki.lib.clients import MerakiClient
from cmk.plugins.cisco_meraki.lib.config import MerakiConfig

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
        client = MerakiClient.build(FakeMerakiSDK(), config)
        return MerakiRunContext(config=config, client=client)

    def test_no_errors(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)
        assert capsys.readouterr().err == ""

    def test_section_headings(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)

        # NOTE: testing on a set here because there could be duplicate matches with multiple orgs.
        value = set(re.findall(r"<<<cisco_meraki_org_(\w+):sep\(0\)>>>", capsys.readouterr().out))
        expected = {
            "device_info",
            "device_status",
            "licenses_overview",
            "organisations",
            "sensor_readings",
        }

        assert value == expected

    def test_piggyback_headings(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)

        value = set(re.findall(r"<<<<(\w+-\w+)>>>>", capsys.readouterr().out))
        expected = {"123-dev1", "123-dev2", "456-dev3"}  # prefixed with org ID

        assert value == expected

    def test_section_specified(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        updated_ctx = _update_section_names(ctx, section_names=["licenses-overview"])
        agent.run(updated_ctx)

        value = re.findall(r"<<<cisco_meraki_org_(\w+):sep\(0\)>>>", capsys.readouterr().out)
        expected = ["organisations", "licenses_overview"]

        assert value == expected

    def test_section_specified_size(
        self, ctx: MerakiRunContext, capsys: CaptureFixture[str]
    ) -> None:
        agent.run(ctx)
        agent_output_all_orgs = capsys.readouterr().out

        updated_ctx = _update_section_names(ctx, section_names=["licenses-overview"])
        agent.run(updated_ctx)
        agent_output_with_org = capsys.readouterr().out

        assert len(agent_output_all_orgs) > len(agent_output_with_org)

    def test_unknown_org(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        updated_ctx = _update_org_ids(ctx, org_ids=["made-up-org"])
        agent.run(updated_ctx)
        assert capsys.readouterr().out == ""

    def test_org_specified_size(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        agent.run(ctx)
        agent_output_all_orgs = capsys.readouterr().out

        updated_ctx = _update_org_ids(ctx, org_ids=["123"])
        agent.run(updated_ctx)
        agent_output_with_org = capsys.readouterr().out

        assert len(agent_output_all_orgs) > len(agent_output_with_org)

    @pytest.mark.usefixtures("patch_storage_env")
    def test_cache_is_being_used(self, ctx: MerakiRunContext, capsys: CaptureFixture[str]) -> None:
        # override resources that aren't cached by default.
        args = agent.parse_arguments([*_DEFAULT_ARGS, "--cache-sensor-readings", "60.0"])
        config = MerakiConfig.build(args)
        client = MerakiClient.build(FakeMerakiSDK(), config)
        ctx = MerakiRunContext(config=config, client=client)

        agent.run(ctx)
        first_run = capsys.readouterr().out
        agent.run(ctx)
        second_run = capsys.readouterr().out

        assert first_run == second_run


def _update_org_ids(ctx: MerakiRunContext, org_ids: Sequence[str]) -> MerakiRunContext:
    patched_config = dataclasses.replace(ctx.config, org_ids=org_ids)
    return dataclasses.replace(ctx, config=patched_config)


def _update_section_names(ctx: MerakiRunContext, section_names: Sequence[str]) -> MerakiRunContext:
    patched_config = dataclasses.replace(ctx.config, section_names=section_names)
    return dataclasses.replace(ctx, config=patched_config)
