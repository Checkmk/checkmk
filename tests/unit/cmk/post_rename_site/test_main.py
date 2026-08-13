#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import logging
import sys

import pytest

from cmk.ccc.site import SiteId
from cmk.post_rename_site import main
from cmk.post_rename_site.internal import Name, RenameAction, SortIndex, Title


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
    def mock_run(*_a: object, **_kw: object) -> bool:
        sys.stdout.write("XYZ\n")
        return False

    monkeypatch.setattr(main, "run", mock_run)

    assert main.main(["old_site_id"]) == 0

    assert "XYZ" in capsys.readouterr().out


@pytest.mark.usefixtures("restore_root_logger_handlers")
def test_run_executes_plugins(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = list[object]()

    def handler_mock(old_site_id: SiteId, new_site_id: SiteId, logger: logging.Logger) -> None:
        args[:] = [old_site_id, new_site_id, logger]

    my_action = RenameAction(
        name=Name("test"),
        title=Title("Test Title"),
        sort_index=SortIndex(),
        run=handler_mock,
    )

    monkeypatch.setattr(main, "load_plugins", lambda *_a, **_kw: [my_action])

    assert main.main(["-v", "old"]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert "1/1 Test Title..." in output.out
    assert output.out.endswith("Done\n")
    assert args == [SiteId("old"), SiteId("NO_SITE"), logging.getLogger("cmk.post_rename_site")]
