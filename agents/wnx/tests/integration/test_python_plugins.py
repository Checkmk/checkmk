#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The agent's Python plugins, run by the interpreter that python-3.cab ships."""

import json
import re
from pathlib import Path

from .utils import http_server, run_python


def test_cab_python_is_the_pinned_version(
    cab_python: Path, repo_root: Path, tmp_path: Path
) -> None:
    pinned = re.findall(
        r'(?m)^PYTHON_VERSION_WINDOWS = "(.+)"$', (repo_root / "package_versions.bzl").read_text()
    )

    result = run_python(
        cab_python, ["-c", "import platform; print(platform.python_version())"], conf_dir=tmp_path
    )

    assert result.stdout.split() == pinned


def test_logwatch_reports_a_matching_line(
    cab_python: Path, repo_root: Path, tmp_path: Path
) -> None:
    logfile = tmp_path / "app.log"
    logfile.write_text("an error occurred\n")
    (tmp_path / "logwatch.cfg").write_text(f'"{logfile.as_posix()}" fromstart=true\n C error\n')

    result = run_python(
        cab_python, [repo_root / "agents/plugins/mk_logwatch.py"], conf_dir=tmp_path
    )

    assert "C an error occurred" in result.stdout.splitlines()


def test_jolokia_reports_the_server_product(
    cab_python: Path, repo_root: Path, tmp_path: Path
) -> None:
    with http_server(
        lambda request: (
            {
                "status": 200,
                "value": {"agent": "1.7.2", "info": {"product": "tomcat", "version": "9.0.98"}},
            }
            if json.loads(request)["type"] == "version"
            else {"status": 404, "error": "not found"}
        )
    ) as port:
        (tmp_path / "jolokia.cfg").write_text(
            f'server = "127.0.0.1"\nport = {port}\ninstance = "test"\nmode = None\ntimeout = 5.0\n'
        )

        result = run_python(
            cab_python, [repo_root / "agents/plugins/mk_jolokia.py"], conf_dir=tmp_path
        )

    assert "test\x00tomcat\x009.0.98\x001.7.2" in result.stdout.splitlines()


def test_postgres_prints_its_usage(cab_python: Path, repo_root: Path, tmp_path: Path) -> None:
    result = run_python(
        cab_python, [repo_root / "agents/plugins/mk_postgres.py", "--help"], conf_dir=tmp_path
    )

    assert result.stdout.startswith("Usage:")
