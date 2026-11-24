# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from cmk_dev_site.utils.update_check import check_for_update, is_newer, upgrade_command

PIPX_PREFIX = "/home/dev/.local/share/pipx/venvs/cmk-dev-site"
DAY = 24 * 60 * 60.0
UPDATE_LINE = "A new version of cmk-dev-site is available: 1.6.1 (you have 1.4.0)."


class FakeClock:
    def __init__(self, start: float) -> None:
        self.time = start

    def __call__(self) -> float:
        return self.time


class FakePyPI:
    def __init__(self, latest: str | None) -> None:
        self.latest = latest
        self.calls = 0

    def __call__(self) -> str | None:
        self.calls += 1
        return self.latest


@pytest.fixture
def cache_file(tmp_path: Path) -> Path:
    return tmp_path / "cache" / "latest-version.json"


def write_cached(cache_file: Path, latest: str, checked_at: float) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"latest": latest, "checked_at": checked_at}))


def run_check(
    cache_file: Path,
    pypi: FakePyPI,
    clock: FakeClock,
    *,
    current_version: str = "1.4.0",
    environ: dict[str, str] | None = None,
    run_seconds: float = 120,
    body: Callable[[], None] = lambda: None,
) -> None:
    with check_for_update(
        current_version=current_version,
        fetch_latest=pypi,
        cache_file=cache_file,
        environ=environ or {},
        install_prefix=PIPX_PREFIX,
        program="cmk-dev-install",
        now=clock,
    ):
        clock.time += run_seconds
        body()


def test_warns_at_start_from_cache_and_again_at_end(
    cache_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clock = FakeClock(start=1000.0)
    write_cached(cache_file, "1.6.1", checked_at=999.0)
    pypi = FakePyPI("1.6.1")
    run_check(cache_file, pypi, clock, body=lambda: print("installing"))  # noqa: T201

    captured = capsys.readouterr()
    assert captured.out == "installing\n"
    assert captured.err.count(UPDATE_LINE) == 2
    assert "Update with: pipx upgrade cmk-dev-site" in captured.err
    assert pypi.calls == 0


def test_short_run_warns_only_once(cache_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock(start=1000.0)
    write_cached(cache_file, "1.6.1", checked_at=999.0)

    run_check(cache_file, FakePyPI("1.6.1"), clock, run_seconds=0.1)

    assert capsys.readouterr().err.count(UPDATE_LINE) == 1


def test_asks_pypi_when_cache_is_missing_and_warns_at_end(
    cache_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clock = FakeClock(start=1000.0)
    pypi = FakePyPI("1.6.1")

    run_check(cache_file, pypi, clock)

    assert pypi.calls == 1
    assert capsys.readouterr().err.count(UPDATE_LINE) == 1
    assert json.loads(cache_file.read_text()) == {"latest": "1.6.1", "checked_at": 1120.0}


def test_asks_pypi_again_after_a_day(cache_file: Path) -> None:
    clock = FakeClock(start=1000.0 + DAY)
    write_cached(cache_file, "1.4.0", checked_at=1000.0)
    pypi = FakePyPI("1.6.1")

    run_check(cache_file, pypi, clock)

    assert pypi.calls == 1
    assert json.loads(cache_file.read_text())["latest"] == "1.6.1"


def test_stays_quiet_when_up_to_date(cache_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_check(cache_file, FakePyPI("1.4.0"), FakeClock(start=1000.0))

    assert capsys.readouterr().err == ""


def test_unreachable_pypi_keeps_the_command_working(
    cache_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_check(cache_file, FakePyPI(None), FakeClock(start=1000.0))

    assert capsys.readouterr().err == ""
    assert not cache_file.exists()


def test_corrupt_cache_is_ignored(cache_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("not json")

    run_check(cache_file, FakePyPI("1.6.1"), FakeClock(start=1000.0))

    assert capsys.readouterr().err.count(UPDATE_LINE) == 1


def test_warns_on_failure_too(cache_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def fail() -> None:
        raise RuntimeError("install failed")

    with pytest.raises(RuntimeError):
        run_check(cache_file, FakePyPI("1.6.1"), FakeClock(start=1000.0), body=fail)

    assert UPDATE_LINE in capsys.readouterr().err


@pytest.mark.parametrize(
    "current_version, environ",
    [
        pytest.param("1.4.0", {"CMK_DEV_SITE_NO_UPDATE_CHECK": "1"}, id="opted-out"),
        pytest.param("0.0.0", {}, id="development-checkout"),
    ],
)
def test_skips_the_check(
    cache_file: Path,
    capsys: pytest.CaptureFixture[str],
    current_version: str,
    environ: dict[str, str],
) -> None:
    pypi = FakePyPI("1.6.1")

    run_check(
        cache_file, pypi, FakeClock(start=1000.0), current_version=current_version, environ=environ
    )

    assert pypi.calls == 0
    assert capsys.readouterr().err == ""


def test_checks_only_once_when_nested(cache_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock(start=1000.0)
    pypi = FakePyPI("1.6.1")

    def nested() -> None:
        run_check(cache_file, pypi, clock)

    run_check(cache_file, pypi, clock, body=nested)

    assert pypi.calls == 1
    assert capsys.readouterr().err.count(UPDATE_LINE) == 1


@pytest.mark.parametrize(
    "latest, current, expected",
    [
        pytest.param("1.6.1", "1.4.0", True, id="newer-minor"),
        pytest.param("1.10.0", "1.9.3", True, id="numeric-not-lexical"),
        pytest.param("2.0.0", "1.23.0", True, id="newer-major"),
        pytest.param("1.4.0", "1.4.0", False, id="same"),
        pytest.param("1.4.0", "1.6.1", False, id="ahead-of-pypi"),
        pytest.param("1.6.1", "1.6.1rc3", True, id="final-beats-its-release-candidate"),
        pytest.param("1.6.0", "1.6.1rc3", False, id="release-candidate-of-next-version"),
        pytest.param("garbage", "1.4.0", False, id="unparsable"),
    ],
)
def test_is_newer(latest: str, current: str, expected: bool) -> None:
    assert is_newer(latest, current) is expected


@pytest.mark.parametrize(
    "install_prefix, expected",
    [
        pytest.param(PIPX_PREFIX, "pipx upgrade cmk-dev-site", id="pipx"),
        pytest.param(
            "/home/dev/.local/pipx/venvs/cmk-dev-site", "pipx upgrade cmk-dev-site", id="old-pipx"
        ),
        pytest.param(
            "/home/dev/.local/share/uv/tools/cmk-dev-site",
            "uv tool upgrade cmk-dev-site",
            id="uv-tool",
        ),
        pytest.param(
            "/home/dev/.cache/uv/archive-v0/CA_-WCrm9_eIA8RzzowZ4",
            "uvx --from cmk-dev-site@latest cmk-dev-install",
            id="uvx",
        ),
        pytest.param("/home/dev/venv", "pip install --upgrade cmk-dev-site", id="other"),
    ],
)
def test_upgrade_command_matches_the_installer(install_prefix: str, expected: str) -> None:
    assert upgrade_command(install_prefix, "cmk-dev-install") == expected
