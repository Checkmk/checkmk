#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.site import SiteId
from cmk.post_rename_site import main
from cmk.post_rename_site.registry import RenameAction, RenameActionRegistry


def test_parse_arguments_verbose() -> None:
    assert main.parse_arguments(["old"]).verbose == 0
    assert main.parse_arguments(["-v", "old"]).verbose == 1
    assert main.parse_arguments(["-v", "-v", "old"]).verbose == 2
    assert main.parse_arguments(["-vv", "old"]).verbose == 2
    assert main.parse_arguments(["-v", "-v", "-v", "old"]).verbose == 3
    assert main.parse_arguments(["-vvv", "old"]).verbose == 3


def test_parse_arguments_debug() -> None:
    assert main.parse_arguments(["old"]).debug is False
    assert main.parse_arguments(["--debug", "old"]).debug is True


def test_parse_argument_site_id(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="2"):
        main.parse_arguments([])
    assert main.parse_arguments(["hurz"]).old_site_id == "hurz"


@pytest.fixture
def restore_root_logger_handlers():
    logger = logging.getLogger()
    before_handlers = list(logger.handlers)
    yield
    logger.handlers = before_handlers


@pytest.mark.usefixtures("restore_root_logger_handlers")
def test_main_executes_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def mock_run(verbose: bool, old_site_id: SiteId, new_site_id: SiteId) -> bool:
        sys.stdout.write("XYZ\n")
        return False

    monkeypatch.setattr(main, "run", mock_run)

    assert main.main(["old_site_id"]) == 0

    assert "XYZ" in capsys.readouterr().out


@pytest.mark.usefixtures("restore_root_logger_handlers")
def test_run_executes_plugins(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = RenameActionRegistry()
    monkeypatch.setattr(main, "rename_action_registry", registry)
    handler_mock = mocker.MagicMock()
    registry.register(
        RenameAction(name="test", title="Test Title", sort_index=0, handler=handler_mock)
    )

    assert main.main(["-v", "old"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert "1/1 Test Title..." in output.out
    assert output.out.endswith("Done\n")
    handler_mock.assert_called_once_with(
        SiteId("old"), SiteId("NO_SITE"), logging.getLogger("cmk.post_rename_site")
    )
