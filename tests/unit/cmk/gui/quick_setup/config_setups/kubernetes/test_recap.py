#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import shlex
from html import escape
from typing import Literal

import pytest
import yaml

from cmk.ccc.site import SiteId
from cmk.gui.quick_setup.config_setups.kubernetes.helm import MonitoringSettings
from cmk.gui.quick_setup.config_setups.kubernetes.recap import deployment_widgets, PushCredentials
from cmk.gui.quick_setup.config_setups.kubernetes.settings import (
    CommonSettings,
    CONNECTION,
    PullSettings,
    PushSettings,
    read_settings,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import Code, ListOfWidgets, Text
from cmk.gui.watolib.configuration_bundle_store import BundleId


@pytest.fixture
def settings() -> PullSettings:
    return PullSettings(
        common=CommonSettings(
            bundle_id=BundleId("monitoring"),
            release_name="monitoring",
            namespace="monitoring",
            monitoring=MonitoringSettings(
                cluster_name="production", host_name="legacy", host_kinds=frozenset({"nodes"})
            ),
            host_path="",
            site_id=SiteId("site"),
        ),
        shared_secret="shared-secret",
    )


def test_pull_downloads_do_not_prepare_push_credentials(settings: PullSettings) -> None:
    def unexpected_push(_settings: PushSettings) -> PushCredentials:
        pytest.fail("Pull mode must not issue a push token or read the site CA")

    widgets = deployment_widgets(settings, prepare_push=unexpected_push)
    files = {
        widget.download_filename: yaml.safe_load(widget.code)
        for widget in widgets
        if isinstance(widget, Code) and widget.download_filename and widget.code
    }

    assert set(files) == {"values.yaml", "pull-secret.yaml"}
    assert base64.b64decode(files["pull-secret.yaml"]["data"]["secret"]).decode() == "shared-secret"
    assert files["values.yaml"]["clusterHostName"] == "legacy"
    assert (
        files["values.yaml"]["pull"]["authentication"]["existingSecret"]["name"]
        == (files["pull-secret.yaml"]["metadata"]["name"])
    )


def test_push_downloads_prepare_credentials_once(settings: PullSettings) -> None:
    calls = []

    def prepare_push(_settings: PushSettings) -> PushCredentials:
        calls.append(True)
        return PushCredentials(
            receiver_url="https://receiver:8000/site",
            registration_token="0:token-id",
            site_ca_certificate="site-ca",
        )

    widgets = deployment_widgets(PushSettings(common=settings.common), prepare_push=prepare_push)
    files = {
        widget.download_filename: yaml.safe_load(widget.code)
        for widget in widgets
        if isinstance(widget, Code) and widget.download_filename and widget.code
    }

    assert calls == [True]
    assert set(files) == {"values.yaml", "push-registration-secret.yaml"}
    assert (
        base64.b64decode(files["push-registration-secret.yaml"]["data"]["token"]) == b"0:token-id"
    )
    assert files["values.yaml"]["push"]["url"] == "https://receiver:8000/site"
    assert all("0:token-id" not in widget.text for widget in widgets if isinstance(widget, Text))


@pytest.mark.parametrize("mode", ["push", "pull"])
def test_deployment_instructions_precede_files_and_runnable_commands(
    data: ParsedFormData, mode: Literal["push", "pull"]
) -> None:
    settings = read_settings(
        {**data, CONNECTION: (mode, {"shared_secret": "shared-secret"})},
        default_site=SiteId("site"),
    )
    widgets = deployment_widgets(
        settings,
        prepare_push=lambda _settings: PushCredentials(
            receiver_url="https://receiver:8000/site",
            registration_token="0:token-id",
            site_ca_certificate="site-ca",
        ),
    )

    headings = [
        widget.text for widget in widgets if isinstance(widget, Text) and "<h2>" in widget.text
    ]
    assert headings == [
        "<h2>Before you deploy</h2>",
        "<h2>Download the deployment files</h2>",
        "<h2>Deploy with Helm</h2>",
    ]
    assert isinstance(widgets[1], ListOfWidgets)
    assert widgets[1].list_type == "bullet"
    assert all(isinstance(widget, Code) and widget.download_filename for widget in widgets[4:6])
    commands = widgets[-1]
    assert isinstance(commands, Code) and commands.code
    assert len(commands.code.splitlines()) == 3
    assert all(not line.startswith("#") for line in commands.code.splitlines())
    helm_command = shlex.split(commands.code.splitlines()[-1])
    version_range = helm_command[helm_command.index("--version") + 1]
    notes = widgets[-2]
    assert isinstance(notes, ListOfWidgets)
    assert any(
        isinstance(note, Text) and f"<b>{escape(version_range)}</b>" in note.text
        for note in notes.items
    )


@pytest.mark.parametrize("mode", ["push", "pull"])
def test_download_instructions_name_the_offered_files(
    data: ParsedFormData, mode: Literal["push", "pull"]
) -> None:
    settings = read_settings(
        {**data, CONNECTION: (mode, {"shared_secret": "shared-secret"})},
        default_site=SiteId("site"),
    )
    widgets = deployment_widgets(
        settings,
        prepare_push=lambda _settings: PushCredentials(
            receiver_url="https://receiver:8000/site",
            registration_token="0:token-id",
            site_ca_certificate="site-ca",
        ),
    )

    (instructions,) = (
        widget for widget in widgets if isinstance(widget, Text) and "Download both" in widget.text
    )
    offered = [
        widget.download_filename
        for widget in widgets
        if isinstance(widget, Code) and widget.download_filename
    ]
    assert len(offered) == 2
    assert all(f"<tt>{filename}</tt>" in instructions.text for filename in offered)
