#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Smoke tests for executable binaries.

If a binary already has its own dedicated test suite, it should not be listed here.
"""

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.testlib.site import Site


@dataclass(frozen=True)
class BinarySmoke:
    """A binary to smoke-test by executing it in the site context."""

    name: str
    args: Sequence[str] = ()
    expected_stdout: str = ".*"
    expected_stderr: str = ".*"
    path: str = ""  # site-relative directory; if empty, name is used directly (must be on PATH)

    def cmd_line(self, site: Site) -> list[str]:
        executable = site.root.joinpath(self.path, self.name).as_posix() if self.path else self.name
        return [executable, *self.args]


@dataclass(frozen=True)
class RepoScript:
    """A script to smoke-test directly from the repository (not installed in site)."""

    name: str
    path: str  # repo-relative path
    args: Sequence[str] = ()
    expected_stdout: str = ".*"
    expected_stderr: str = ".*"


# Notification plugins — expect KeyError because they need environment variables
_NOTIF_PATH = "share/check_mk/notifications"
NOTIFICATION_PLUGINS: Sequence[BinarySmoke] = [
    BinarySmoke("asciimail", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("cisco_webex_teams", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("flowtriq", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("ilert", expected_stderr=r"IndexError.*list index out of range", path=_NOTIF_PATH),
    BinarySmoke("mail", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("msteams", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("opsgenie_issues", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("pagerduty", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("pushover", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("signl4", expected_stderr=r"IndexError.*list index out of range", path=_NOTIF_PATH),
    BinarySmoke("slack", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("sms", expected_stderr=r"(KeyError.*NOTIF|SMS Tools binaries)", path=_NOTIF_PATH),
    BinarySmoke("sms_api", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("spectrum", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("victorops", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
]

# bin/ binaries — on the site's PATH, no path needed
BIN_BINARIES: Sequence[BinarySmoke] = [
    BinarySmoke("check_mk"),
    BinarySmoke("cmk-cert", args=["-h"], expected_stdout=r"usage:.*cmk-cert"),
    BinarySmoke("cmk-create-rrd", args=["-h"], expected_stdout=r"usage:.*cmk-create-rrd"),
    BinarySmoke(
        "cmk-migrate-extension-rulesets",
        args=["-h"],
        expected_stdout=r"usage:.*cmk-migrate-extension-rulesets",
    ),
    BinarySmoke("cmk-passwd", args=["-h"], expected_stdout=r"usage:.*cmk-passwd"),
    BinarySmoke(
        "cmk-transform-inventory-trees",
        args=["-h"],
        expected_stdout=r"usage:.*cmk-transform-inventory-trees",
    ),
    BinarySmoke("cmk-ui-job-scheduler"),
    BinarySmoke("cmk-update-config", args=["-h"], expected_stdout=r"usage:.*cmk-update-config"),
    BinarySmoke("cmk-validate-config"),
    BinarySmoke("livedump", args=["-h"], expected_stdout=r"usage:.*livedump"),
    BinarySmoke("post-rename-site", args=["-h"], expected_stdout=r"usage:.*post-rename-site"),
]

# Non-free binaries available in pro and above (skip on community)
NONFREE_PRO_BINARIES: Sequence[BinarySmoke] = [
    BinarySmoke("jira_issues", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("jsm_operations", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
    BinarySmoke("servicenow", expected_stderr=r"KeyError.*NOTIF", path=_NOTIF_PATH),
]

# Non-free binaries available in ultimate and ultimatemt only (not cloud, community, or pro).
# Cloud ships cmk-otel-collector but NOT the otel-collector package with this cleanup script.
NONFREE_ULTIMATE_BINARIES: Sequence[BinarySmoke] = [
    BinarySmoke(
        "cmk-cleanup-otel-collector-files",
        args=["-h"],
        expected_stdout=r"(usage:.*cmk_cleanup|older-than)",
    ),
]

ALL_SITE_BINARIES: Sequence[BinarySmoke] = [*NOTIFICATION_PLUGINS, *BIN_BINARIES]

# Build/dev scripts that are not installed in the site
REPO_SCRIPTS: Sequence[RepoScript] = [
    RepoScript(
        "strip_binaries",
        "omd/strip_binaries",
        args=["-h"],
        expected_stdout=r"(usage:.*strip_binaries|strip)",
    ),
    RepoScript(
        "decent-output",
        "scripts/decent-output",
        expected_stderr=r"(decent|timeout|IndexError|ValueError)",
    ),
]


@pytest.mark.parametrize(
    "binary",
    (pytest.param(b, id=b.name) for b in ALL_SITE_BINARIES),
)
def test_binary_smoke(binary: BinarySmoke, site: Site) -> None:
    """Run binary in site context and verify it produces expected output."""
    p = site.run(binary.cmd_line(site), check=False)
    assert re.search(binary.expected_stdout, p.stdout, re.DOTALL)
    assert re.search(binary.expected_stderr, p.stderr, re.DOTALL)


@pytest.mark.skip_if_not_edition("pro", "ultimate", "ultimatemt", "cloud")
@pytest.mark.parametrize(
    "binary",
    (pytest.param(b, id=b.name) for b in NONFREE_PRO_BINARIES),
)
def test_binary_smoke_pro(binary: BinarySmoke, site: Site) -> None:
    """Run pro+ binary in site context and verify it produces expected output."""
    p = site.run(binary.cmd_line(site), check=False)
    assert re.search(binary.expected_stdout, p.stdout, re.DOTALL)
    assert re.search(binary.expected_stderr, p.stderr, re.DOTALL)


@pytest.mark.skip_if_not_edition("ultimate", "ultimatemt")
@pytest.mark.parametrize(
    "binary",
    (pytest.param(b, id=b.name) for b in NONFREE_ULTIMATE_BINARIES),
)
def test_binary_smoke_ultimate(binary: BinarySmoke, site: Site) -> None:
    """Run ultimate+ binary in site context and verify it produces expected output."""
    p = site.run(binary.cmd_line(site), check=False)
    assert re.search(binary.expected_stdout, p.stdout, re.DOTALL)
    assert re.search(binary.expected_stderr, p.stderr, re.DOTALL)


@pytest.mark.parametrize(
    "script",
    (pytest.param(s, id=s.name) for s in REPO_SCRIPTS),
)
def test_repo_script_smoke(script: RepoScript) -> None:
    """Run build/dev scripts from the repository that are not installed in the site."""
    repo_root = Path(__file__).parent.parent.parent
    binary_path = repo_root / script.path

    assert binary_path.exists(), f"Script not found: {binary_path}"

    result = subprocess.run(
        [str(binary_path), *script.args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert re.search(script.expected_stdout, result.stdout, re.DOTALL)
    assert re.search(script.expected_stderr, result.stderr, re.DOTALL)
