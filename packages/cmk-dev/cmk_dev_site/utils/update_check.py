# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import re
import sys
import threading
import time
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import requests

from ..version import __version__
from .log import colorize

PACKAGE = "cmk-dev-site"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE}/json"
OPT_OUT_VARIABLE = "CMK_DEV_SITE_NO_UPDATE_CHECK"

_DEV_VERSION = "0.0.0"
_CHECK_INTERVAL = 24 * 60 * 60.0
_FETCH_TIMEOUT = 3.0
_FETCH_WAIT_AT_EXIT = 0.2
_MIN_RUN_FOR_SECOND_WARNING = 1.0
_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)*)(.*)")

_check_active = False


@dataclass(frozen=True)
class CachedVersion:
    latest: str
    checked_at: float


def fetch_latest_version() -> str | None:
    try:
        response = requests.get(PYPI_URL, timeout=_FETCH_TIMEOUT)
        response.raise_for_status()
        payload: object = response.json()
    except requests.RequestException, ValueError:
        return None
    version = _field(_field(payload, "info"), "version")
    return version if isinstance(version, str) else None


def _field(data: object, key: str) -> object:
    return cast(dict[str, object], data).get(key) if isinstance(data, dict) else None


def default_cache_file(environ: Mapping[str, str]) -> Path:
    cache_home = environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache_home) / PACKAGE / "latest-version.json"


def read_cache(path: Path) -> CachedVersion | None:
    try:
        data: object = json.loads(path.read_text())
    except OSError, ValueError:
        return None
    latest = _field(data, "latest")
    checked_at = _field(data, "checked_at")
    if not isinstance(latest, str) or not isinstance(checked_at, int | float):
        return None
    return CachedVersion(latest=latest, checked_at=float(checked_at))


def write_cache(path: Path, cached: CachedVersion) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"latest": cached.latest, "checked_at": cached.checked_at}))
    except OSError:
        pass


def _split_version(version: str) -> tuple[tuple[int, ...], str] | None:
    if not (match := _VERSION_PATTERN.fullmatch(version)):
        return None
    release = tuple(int(part) for part in match.group(1).split("."))
    return release, match.group(2)


def is_newer(latest: str, current: str) -> bool:
    """Compare release numbers; a final release beats a pre-release (e.g. 1.6.1 > 1.6.1rc3)."""
    if (latest_parts := _split_version(latest)) is None or (
        current_parts := _split_version(current)
    ) is None:
        return False
    latest_release, latest_suffix = latest_parts
    current_release, current_suffix = current_parts
    if latest_release != current_release:
        return latest_release > current_release
    return bool(current_suffix) and not latest_suffix


def upgrade_command(install_prefix: str, program: str) -> str:
    """Guess how the tool was installed from the location of its Python environment."""
    location = Path(install_prefix).as_posix() + "/"
    if "/pipx/venvs/" in location:
        return f"pipx upgrade {PACKAGE}"
    if "/uv/tools/" in location:
        return f"uv tool upgrade {PACKAGE}"
    if "/uv/archive-v" in location:
        return f"uvx --from {PACKAGE}@latest {program}"
    return f"pip install --upgrade {PACKAGE}"


def _warn_if_outdated(latest: str | None, current: str, command: str, prefix: str = "") -> bool:
    if latest is None or not is_newer(latest, current):
        return False
    message = (
        f"A new version of {PACKAGE} is available: {latest} (you have {current}).\n"
        f"Update with: {command}"
    )
    print(prefix + colorize(message, "yellow"), file=sys.stderr)  # noqa: T201
    return True


class _BackgroundFetch:
    def __init__(self, fetch: Callable[[], str | None]) -> None:
        self._fetch = fetch
        self._result: str | None = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._result = self._fetch()

    def result(self, wait: float) -> str | None:
        self._thread.join(timeout=wait)
        return None if self._thread.is_alive() else self._result


@contextmanager
def check_for_update(
    *,
    current_version: str = __version__,
    fetch_latest: Callable[[], str | None] = fetch_latest_version,
    cache_file: Path | None = None,
    environ: Mapping[str, str] = os.environ,
    install_prefix: str = sys.prefix,
    program: str | None = None,
    now: Callable[[], float] = time.time,
) -> Generator[None]:
    """Warn on stderr, before and after the wrapped command, when PyPI has a newer version.

    The start uses the cached answer so it never waits on the network; PyPI is asked
    at most once a day in the background and the answer is used at the end. Only the
    outermost use checks, so nested commands don't warn twice. Set
    CMK_DEV_SITE_NO_UPDATE_CHECK to turn the check off.
    """
    global _check_active  # pylint: disable=global-statement
    if _check_active or environ.get(OPT_OUT_VARIABLE) or current_version == _DEV_VERSION:
        yield
        return

    _check_active = True
    started = now()
    cache_path = cache_file or default_cache_file(environ)
    command = upgrade_command(install_prefix, program or Path(sys.argv[0]).name)

    cached = read_cache(cache_path)
    warned_at_start = _warn_if_outdated(cached and cached.latest, current_version, command)  # type: ignore[arg-type]
    stale = cached is None or not 0 <= started - cached.checked_at < _CHECK_INTERVAL
    background = _BackgroundFetch(fetch_latest) if stale else None

    try:
        yield
    finally:
        _check_active = False
        latest = cached and cached.latest
        if background and (fetched := background.result(_FETCH_WAIT_AT_EXIT)):
            write_cache(cache_path, CachedVersion(latest=fetched, checked_at=now()))
            latest = fetched
        if not warned_at_start or now() - started >= _MIN_RUN_FOR_SECOND_WARNING:
            _warn_if_outdated(latest, current_version, command, prefix="\n")  # type: ignore[arg-type]
