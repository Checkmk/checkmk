#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import sys

import pytest

from tests.testlib import is_enterprise_repo

from livestatus import SiteId

from cmk.post_rename_site import main
from cmk.post_rename_site.registry import rename_action_registry, RenameAction, RenameActionRegistry


@pytest.fixture(autouse=True)
def ensure_logging_framework_not_altered():
    logger = logging.getLogger()
    before_handlers = list(logger.handlers)
    yield
    logger.handlers = before_handlers


def test_parse_arguments_defaults():
    assert main.parse_arguments(["old"]).__dict__ == {
        "debug": False,
        "verbose": 0,
        "old_site_id": SiteId("old"),
    }


def test_parse_arguments_missing_old_site_id(capsys):
    with pytest.raises(SystemExit, match="2"):
        main.parse_arguments([])
    assert "required: OLD_SITE_ID" in capsys.readouterr().err


def test_parse_arguments_verbose():
    assert main.parse_arguments(["-v", "old"]).verbose == 1
    assert main.parse_arguments(["-v", "-v", "old"]).verbose == 2
    assert main.parse_arguments(["-v", "-v", "-v", "old"]).verbose == 3


def test_parse_arguments_debug():
    assert main.parse_arguments(["--debug", "old"]).debug is True


def test_main_executes_run(monkeypatch, capsys):
    def mock_run(args: argparse.Namespace, old_site_id: SiteId, new_site_id: SiteId) -> bool:
        sys.stdout.write("XYZ\n")
        return False

    monkeypatch.setattr(main, "run", mock_run)
    assert main.main(["old_site_id"]) == 0
    assert "XYZ" in capsys.readouterr().out


@pytest.fixture(name="test_registry")
def fixture_test_registry(monkeypatch):
    registry = RenameActionRegistry()
    monkeypatch.setattr(main, "rename_action_registry", registry)
    return registry


def test_run_executes_plugins(capsys, test_registry, mocker):
    handler_mock = mocker.MagicMock()
    test_registry.register(
        RenameAction(name="test", title="Test Title", sort_index=0, handler=handler_mock)
    )

    assert main.main(["-v", "old"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert "1/1 Test Title..." in output.out
    assert output.out.endswith("Done\n")

    assert handler_mock.called_once_with(SiteId("old"), SiteId("NO_SITE"))


def test_load_plugins():
    main.load_plugins()
    expected = [
        "sites",
        "hosts_and_folders",
        "update_core_config",
        "warn_remote_site",
        "warn_about_network_ports",
        "warn_about_configs_to_review",
    ]

    if is_enterprise_repo():
        expected.append("dcd_connections")

    assert sorted(rename_action_registry.keys()) == sorted(expected)
