#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Regenerate the pinned win_amd64 wheel closure for ``python-3.cab``.

The Windows agent CAB ships the Pipfile packages (and their transitive
dependencies) as win_amd64/cp3xx wheels.  Those wheels are fetched in Bazel's
fetch/repository phase from pinned ``http_file`` repos (see
``windows_python_wheels.bzl``), so the ``python_cab`` build action stays
hermetic.  This tool resolves the full transitive closure and writes
``windows_python_wheels.lock.json`` (url + sha256 per wheel).

The requirement specs come from ``pipfiles/3/Pipfile`` ``[packages]`` — keep that
file, ``BUILD.bazel``'s ``requirements`` list, and this lock in lockstep.

Run after bumping ``PYTHON_VERSION_WINDOWS`` in ``defines.make`` or after editing
the Pipfile.  Prefer running under the hermetic interpreter so the resolving pip
matches the one the build action installs with:

    bazel run //agents/modules/windows:refresh_wheel_pins -- 3.13.13

``--check`` exits non-zero if the on-disk lock is stale (for CI).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

# Under `bazel run`, __file__ lives in the runfiles sandbox; BUILD_WORKSPACE_DIRECTORY
# points at the real source tree so we read the Pipfile and write the lock there.
_workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
_HERE = (
    Path(_workspace) / "agents" / "modules" / "windows"
    if _workspace
    else Path(__file__).resolve().parent
)
_PIPFILE = _HERE / "pipfiles" / "3" / "Pipfile"
_LOCK = _HERE / "windows_python_wheels.lock.json"
_ALLOWED_HOST = "files.pythonhosted.org"

# Shipped in addition to the Pipfile packages: the historic Windows build
# seeded pip into the CAB's .venv (via virtualenv) and upgraded the base
# interpreter's pip (via pipenv), so customers could extend the agent's
# Python with `.venv\Scripts\pip install`.  Keep that surface.  Bump
# this pin together with the Pipfile when refreshing the lock.
_SEED_REQUIREMENTS = ["pip==26.1.1"]


def _pipfile_requirements(pipfile: Path) -> list[str]:
    """Turn ``[packages]`` entries into pip requirement specifiers."""
    data = tomllib.loads(pipfile.read_text())
    specs: list[str] = []
    for name, value in data.get("packages", {}).items():
        if isinstance(value, str):
            specs.append(f"{name}{value}")
            continue
        # Inline-table form, e.g. requests = {extras = ["socks"], version = "2.31.0"}.
        extras = value.get("extras")
        version = value.get("version", "")
        extra_suffix = "[%s]" % ",".join(extras) if extras else ""
        # A bare "2.31.0" version means "==2.31.0" in Pipfile semantics.
        if version and version[0] not in "=<>~!":
            version = f"=={version}"
        specs.append(f"{name}{extra_suffix}{version}")
    return specs


def _resolve_closure(python_version: str, requirements: list[str]) -> list[dict[str, str]]:
    """Resolve the win_amd64 wheel closure via ``pip install --dry-run --report``."""
    major_minor = ".".join(python_version.split(".")[:2])  # "3.13"
    abi = "cp" + major_minor.replace(".", "")  # "cp313"

    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as report:
        report_path = Path(report.name)
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--quiet",
                # Without --ignore-installed, deps already satisfied in the
                # resolving environment are dropped from the report.
                "--ignore-installed",
                "--report",
                str(report_path),
                "--platform",
                "win_amd64",
                "--abi",
                abi,
                "--python-version",
                major_minor,
                "--implementation",
                "cp",
                # Fail loudly if any (transitive) dep lacks a win_amd64 wheel
                # rather than silently building from an sdist.
                "--only-binary=:all:",
                *requirements,
            ],
            check=True,
        )
        report_data = json.loads(report_path.read_text())
    finally:
        report_path.unlink(missing_ok=True)

    wheels: list[dict[str, str]] = []
    for entry in report_data.get("install", []):
        download = entry["download_info"]
        url = download["url"]
        host = urlsplit(url).netloc
        if host != _ALLOWED_HOST:
            sys.exit(
                f"error: {entry['metadata']['name']} resolves to a non-{_ALLOWED_HOST} "
                f"url ({url}). The fetch phase may not reach it — pin a pythonhosted "
                f"wheel or add a mirror fallback before committing the lock."
            )
        wheels.append(
            {
                "name": entry["metadata"]["name"],
                "version": entry["metadata"]["version"],
                "filename": url.rsplit("/", 1)[-1],
                "url": url,
                "sha256": download["archive_info"]["hashes"]["sha256"],
            }
        )
    return sorted(wheels, key=lambda w: w["filename"])


def _render_lock(python_version: str, wheels: list[dict[str, str]]) -> str:
    return json.dumps({"python_version": python_version, "wheels": wheels}, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python_version", help="Full Windows Python version, e.g. 3.13.13")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the on-disk lock differs from a fresh resolution.",
    )
    args = parser.parse_args()

    wheels = _resolve_closure(
        args.python_version, _pipfile_requirements(_PIPFILE) + _SEED_REQUIREMENTS
    )
    rendered = _render_lock(args.python_version, wheels)

    if args.check:
        current = _LOCK.read_text() if _LOCK.exists() else ""
        if current != rendered:
            print(
                f"error: {_LOCK.name} is stale; rerun "
                f"`bazel run //agents/modules/windows:refresh_wheel_pins -- {args.python_version}`",
                file=sys.stderr,
            )
            return 1
        print(f"{_LOCK.name} is up to date ({len(wheels)} wheels).")
        return 0

    _LOCK.write_text(rendered)
    print(f"Wrote {_LOCK} ({len(wheels)} wheels).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
