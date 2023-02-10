#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import MutableMapping
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import cmk.utils.paths

from cmk.update_config import main, registry


@pytest.fixture(autouse=True)
def ensure_logging_framework_not_altered():
    logger = logging.getLogger()
    before_handlers = list(logger.handlers)
    yield
    logger.handlers = before_handlers


def test_parse_arguments_defaults() -> None:
    default_args = main._parse_arguments([])
    assert not default_args.debug
    assert not default_args.verbose


@pytest.mark.parametrize(
    ["v_level"],
    [(v_level,) for v_level in range(4)],
)
def test_parse_arguments_verbose(v_level: int) -> None:
    assert main._parse_arguments(["-v"] * v_level).verbose == v_level


def test_parse_arguments_debug() -> None:
    assert main._parse_arguments(["--debug"]).debug is True


def test_main_calls_config_updater(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    packages_dir = Path(cmk.utils.paths.var_dir, "packages")
    packages_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "installed_packages_dir", packages_dir)
    mock_config_udpater_call = mocker.patch.object(
        main.ConfigUpdater,
        "__call__",
        return_value=False,
    )
    assert not main.main([])
    mock_config_udpater_call.assert_called_once()


class MockUpdateAction(registry.UpdateAction):
    def __init__(self, name: str, title: str, sort_index: int) -> None:
        super().__init__(name=name, title=title, sort_index=sort_index)
        self.calls = 0

    def __call__(self, logger: logging.Logger, update_state: MutableMapping[str, str]) -> None:
        self.calls += 1


def test_config_updater_executes_plugins(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packages_dir = Path(cmk.utils.paths.var_dir, "packages")
    packages_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cmk.utils.paths, "installed_packages_dir", packages_dir)
    reg = registry.UpdateActionRegistry()
    reg.register(
        mock_plugin := MockUpdateAction(
            name="test",
            title="Test Title",
            sort_index=4,
        )
    )
    mocker.patch.object(main, "update_action_registry", reg)
    mocker.patch.object(main.ConfigUpdater, "_initialize_base_environment")

    assert not main.main(["-v"])

    output = capsys.readouterr()
    assert output.err == ""
    assert "1/1 Test Title..." in output.out
    assert output.out.endswith("Done\n")

    assert mock_plugin.calls == 1


def test_load_plugins() -> None:
    main._load_plugins(logging.getLogger())
    assert main.update_action_registry
