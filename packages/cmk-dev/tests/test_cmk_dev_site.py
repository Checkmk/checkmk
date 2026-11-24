# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from datetime import date, datetime, UTC
from unittest.mock import create_autospec, NonCallableMagicMock

import pytest
from cmk_dev_site import cmk_dev_site as cmk_dev_site_module
from cmk_dev_site.cmk_dev_site import (
    Config,
    create_parser,
    handle_site_creation,
    setup_parser,
    Site,
    trial_mode_selection,
)
from cmk_dev_site.omd import (
    BaseVersion,
    CMKPackage,
    Edition,
    VersionWithPatch,
    VersionWithReleaseDate,
)


def test_default_name_base_version() -> None:
    version = BaseVersion(2, 3, 0)
    assert Config._default_name(version) == "v230"  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001


def test_default_name_version_with_patch() -> None:
    version = VersionWithPatch(BaseVersion(2, 3, 0), "p", 1)
    assert Config._default_name(version) == "v230p1"  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001


def test_default_name_version_with_release_date() -> None:
    version = VersionWithReleaseDate(BaseVersion(2, 3, 0), date(2025, 1, 1))
    assert Config._default_name(version) == "v230"  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001


def _ultimate_site() -> Site:
    """A 3.0.0 ultimate site: a version and edition that ships the MCP hooks."""
    return Site("v300", CMKPackage(BaseVersion(3, 0, 0), Edition.ULTIMATE))


@pytest.fixture(name="config_calls")
def _config_calls(  # pyright: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, str]]:
    """Record the (key, value) of every `omd config set` the site performs."""
    calls: list[tuple[str, str]] = []

    def record(_site_name: str, key: str, value: str) -> None:
        calls.append((key, value))

    monkeypatch.setattr(cmk_dev_site_module, "omd_config_set", record)
    return calls


@pytest.fixture(name="new_site")
def _new_site(  # pyright: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch,
) -> NonCallableMagicMock:
    """A mocked site that does not exist yet, recording every step taken on it."""

    def no_existing_site(_site_name: str) -> None:
        return None

    monkeypatch.setattr(cmk_dev_site_module, "find_version_by_site_name", no_existing_site)
    site = create_autospec(Site, instance=True)
    site.name = "v300"
    site.is_remote_site = False
    return site  # type: ignore[no-any-return]


def _set_hooks_available(
    monkeypatch: pytest.MonkeyPatch, available: set[str]
) -> list[tuple[str, str]]:
    """Stub `omd_hook_exists`, recording each `(omd_version, hook_name)` probe call.

    A hook is reported available exactly when its name is in `available`. The
    returned list lets a test assert both the recorded calls and, indirectly
    via `config_calls`, what `configure_site` did with the answer.
    """
    calls: list[tuple[str, str]] = []

    def probe(omd_version: str, hook_name: str) -> bool:
        calls.append((omd_version, hook_name))
        return hook_name in available

    monkeypatch.setattr(cmk_dev_site_module, "omd_hook_exists", probe)
    return calls


def test_configure_site_enables_mcp_when_hooks_available(
    monkeypatch: pytest.MonkeyPatch, config_calls: list[tuple[str, str]]
) -> None:
    hook_calls = _set_hooks_available(monkeypatch, {"MCP_SERVER", "MCP_TRACE_FORWARD"})

    _ultimate_site().configure_site([])

    assert config_calls == [
        ("LIVESTATUS_TCP", "on"),
        ("MCP_SERVER", "on"),
        ("MCP_TRACE_FORWARD", "on"),
    ]
    # The gate must probe the omd version (not e.g. `str(cmk_pkg.version)`, which
    # would be missing the edition suffix and never match an installed hook path).
    assert hook_calls == [
        ("3.0.0.ultimate", "MCP_SERVER"),
        ("3.0.0.ultimate", "MCP_TRACE_FORWARD"),
    ]


def test_configure_site_skips_mcp_when_hooks_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Setting a hook the installation does not know about makes `omd config
    set` write to stderr, which surfaces as a warning. Versions before 3.0.0
    and the community edition must therefore stay untouched and quiet."""
    unavailable_hooks = {"MCP_SERVER", "MCP_TRACE_FORWARD"}
    calls: list[tuple[str, str]] = []

    def set_config(_site_name: str, key: str, value: str) -> None:
        # Mirrors real `omd config set` on an unknown variable: writes to
        # stderr and exits 0, which `omd_config_set` turns into a RuntimeError.
        if key in unavailable_hooks:
            raise RuntimeError(f"No such variable '{key}'")
        calls.append((key, value))

    monkeypatch.setattr(cmk_dev_site_module, "omd_config_set", set_config)
    _set_hooks_available(monkeypatch, set())

    with caplog.at_level(logging.WARNING, logger=cmk_dev_site_module.logger.name):
        _ultimate_site().configure_site([])

    assert calls == [("LIVESTATUS_TCP", "on")]
    assert caplog.records == []


def test_configure_site_enables_only_the_available_mcp_hook(
    monkeypatch: pytest.MonkeyPatch,
    config_calls: list[tuple[str, str]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Hook availability is per hook name, not per version/edition as a whole:
    MCP_SERVER may ship without MCP_TRACE_FORWARD, or vice versa."""
    _set_hooks_available(monkeypatch, {"MCP_SERVER"})

    with caplog.at_level(logging.INFO, logger=cmk_dev_site_module.logger.name):
        _ultimate_site().configure_site([])

    assert ("MCP_SERVER", "on") in config_calls
    assert all(key != "MCP_TRACE_FORWARD" for key, _ in config_calls)
    assert "Forwarding MCP usage data" not in caplog.text


def test_configure_site_explicit_omd_config_overrides_mcp_default(
    monkeypatch: pytest.MonkeyPatch, config_calls: list[tuple[str, str]]
) -> None:
    _set_hooks_available(monkeypatch, {"MCP_SERVER", "MCP_TRACE_FORWARD"})

    _ultimate_site().configure_site([("MCP_SERVER", "off")])

    assert [value for key, value in config_calls if key == "MCP_SERVER"] == ["off"]


def test_configure_site_announces_mcp_usage_data_forwarding(
    monkeypatch: pytest.MonkeyPatch,
    config_calls: list[tuple[str, str]],  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Forwarding usage data to Checkmk must not be a silent default."""
    _set_hooks_available(monkeypatch, {"MCP_SERVER", "MCP_TRACE_FORWARD"})

    with caplog.at_level(logging.INFO, logger=cmk_dev_site_module.logger.name):
        _ultimate_site().configure_site([])

    assert "MCP_TRACE_FORWARD=off" in caplog.text


def test_configure_site_no_forwarding_notice_when_set_explicitly(
    monkeypatch: pytest.MonkeyPatch,
    config_calls: list[tuple[str, str]],  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_hooks_available(monkeypatch, {"MCP_SERVER", "MCP_TRACE_FORWARD"})

    with caplog.at_level(logging.INFO, logger=cmk_dev_site_module.logger.name):
        _ultimate_site().configure_site([("MCP_TRACE_FORWARD", "on")])

    assert "MCP_TRACE_FORWARD=off" not in caplog.text


def test_trial_mode_selection_records_a_trial_selection() -> None:
    selected_at = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)

    assert json.loads(trial_mode_selection(selected_at)) == {
        "selection": "trial",
        "selected_by": "cmkadmin",
        "selected_at": "2026-10-20T09:30:00+00:00",
    }


def test_handle_site_creation_preselects_trial_mode_after_site_creation(
    new_site: NonCallableMagicMock,
) -> None:
    handle_site_creation(
        new_site,
        force=False,
        configs=[],
        show_trial_mode_selection=False,
        enable_ai_assistant=False,
    )

    steps = [step for step, _args, _kwargs in new_site.method_calls]
    assert steps.index("preselect_trial_mode") > steps.index("create_site")


def test_handle_site_creation_keeps_the_trial_mode_selection_on_request(
    new_site: NonCallableMagicMock,
) -> None:
    handle_site_creation(
        new_site,
        force=False,
        configs=[],
        show_trial_mode_selection=True,
        enable_ai_assistant=False,
    )

    new_site.preselect_trial_mode.assert_not_called()


@pytest.mark.parametrize(
    ("ai_assistant_installed", "written_files"),
    [
        pytest.param(True, ["release_flag.json", "_pending_release_flag.json"], id="installed"),
        pytest.param(False, [], id="not-installed"),
    ],
)
def test_enable_ai_assistant_flag_writes_both_flag_files_only_with_the_ai_assistant(
    monkeypatch: pytest.MonkeyPatch, ai_assistant_installed: bool, written_files: list[str]
) -> None:
    calls: list[tuple[list[str], object]] = []

    def init_script_exists(omd_version: str, service_name: str) -> bool:
        return ai_assistant_installed and (omd_version, service_name) == (
            "3.0.0.ultimate",
            "ai-control-plane",
        )

    def record(cmd: list[str], *, input: str = "", **_kwargs: object) -> None:  # noqa: A002
        calls.append((cmd, json.loads(input)))

    monkeypatch.setattr(cmk_dev_site_module, "omd_init_script_exists", init_script_exists)
    monkeypatch.setattr(cmk_dev_site_module, "run_command", record)

    _ultimate_site().enable_ai_assistant_flag()

    assert calls == [
        (
            ["sudo", "su", "-", "v300", "-c", f"tee /omd/sites/v300/etc/check_mk/{name}"],
            {"exp_ai_assistant": True},
        )
        for name in written_files
    ]


def test_handle_site_creation_turns_on_the_ai_assistant_flag_before_configuring_the_site(
    new_site: NonCallableMagicMock,
) -> None:
    handle_site_creation(
        new_site,
        force=False,
        configs=[],
        show_trial_mode_selection=False,
        enable_ai_assistant=True,
    )

    steps = [step for step, _args, _kwargs in new_site.method_calls]
    assert (
        steps.index("create_site")
        < steps.index("enable_ai_assistant_flag")
        < steps.index("configure_site")
    )


@pytest.mark.parametrize(
    ("is_remote_site", "enable_ai_assistant"),
    [
        pytest.param(False, False, id="opted-out"),
        pytest.param(True, True, id="remote-site"),
    ],
)
def test_handle_site_creation_leaves_the_ai_assistant_flag_off(
    new_site: NonCallableMagicMock, is_remote_site: bool, enable_ai_assistant: bool
) -> None:
    new_site.is_remote_site = is_remote_site

    handle_site_creation(
        new_site,
        force=False,
        configs=[],
        show_trial_mode_selection=False,
        enable_ai_assistant=enable_ai_assistant,
    )

    new_site.enable_ai_assistant_flag.assert_not_called()


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        pytest.param([], False, id="default-off"),
        pytest.param(["--ai-assistant"], True, id="opt-in"),
    ],
)
def test_parser_turns_on_the_ai_assistant_flag_only_on_request(
    argv: list[str], expected: bool
) -> None:
    parser = create_parser()
    setup_parser(parser)

    assert parser.parse_args(argv).enable_ai_assistant is expected
