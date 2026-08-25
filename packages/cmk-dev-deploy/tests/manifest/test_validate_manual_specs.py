# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for _validate_manual_specs."""

import os
from pathlib import Path

import pytest

from cmk.dev_deploy.manifest.update import (
    _load_specs_from_toml,
    _validate_manual_specs,
    specs_path,
)
from cmk.dev_deploy.types import Service


def _workspace_root() -> Path | None:
    env = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if env:
        return Path(env)
    candidate = specs_path().resolve().parent
    for _ in range(10):
        if (candidate / "MODULE.bazel").is_file():
            return candidate
        candidate = candidate.parent
    return None


def test_collects_all_stale_references(tmp_path: Path) -> None:
    manual = {
        "service_specs": [
            {"name": "svc_a", "package_target": "//nope:x", "source_prefix": "nope/"},
        ],
        "install_specs": [
            {"name": "pkg_b", "package_target": "//also/missing:y"},
        ],
    }
    with pytest.raises(ValueError) as exc_info:
        _validate_manual_specs(manual, tmp_path)
    msg = str(exc_info.value)
    assert "source_prefix 'nope/' does not exist" in msg
    assert "package_target '//nope:x' does not exist" in msg
    assert "package_target '//also/missing:y' does not exist" in msg


def test_real_deploy_specs_point_at_existing_paths() -> None:
    """The checked-in deploy_specs.toml must reference live paths."""
    repo_root = _workspace_root()
    if repo_root is None:
        pytest.skip("workspace root not accessible (sandbox run)")
    manual = _load_specs_from_toml(specs_path(), (repo_root / "non-free").is_dir())
    _validate_manual_specs(manual, repo_root)


def test_cmk_mcp_wheel_restarts_the_mcp_server_daemon() -> None:
    """Deploying the cmk-mcp wheel restarts the standalone mcp-server daemon.

    The daemon imports cmk.mcp once at startup, so a reinstalled wheel is only
    picked up after a restart.
    """
    repo_root = _workspace_root()
    if repo_root is None:
        pytest.skip("workspace root not accessible (sandbox run)")
    if not (repo_root / "non-free").is_dir():
        pytest.skip("cmk-mcp is a non-free package; not present in this checkout")

    manual = _load_specs_from_toml(specs_path(), is_nonfree_checkout=True)
    mcp = next(
        (
            s
            for s in manual["service_specs"]
            if s["package_target"] == "//non-free/packages/cmk-mcp:wheel"
        ),
        None,
    )

    assert mcp is not None, "no [[service]] entry for the cmk-mcp wheel"
    assert mcp["services"] == ["mcp-server:restart"]
    assert Service("mcp-server") is Service.MCP_SERVER


def test_frontend_vue_dist_reloads_apache() -> None:
    """Deploying the cmk-frontend-vue dist must reload apache.

    The GUI resolves the hashed bundle filenames from the dist's
    .manifest.json once per apache process (lru_cache in
    cmk.gui.htmllib.html); without a reload pages keep referencing the
    replaced bundles.
    """
    manual = _load_specs_from_toml(specs_path(), is_nonfree_checkout=False)
    vue = next(
        (
            s
            for s in manual["service_specs"]
            if s["package_target"] == "//packages/cmk-frontend-vue:frontend_vue_dist_pkg"
        ),
        None,
    )
    assert vue is not None, "no [[service]] entry for the cmk-frontend-vue dist"
    assert vue["services"] == ["apache:reload"]
    # The derived prefix makes both matching tiers fire: changed files under
    # packages/cmk-frontend-vue/ and the resolved dist target package.
    assert vue["source_prefix"] == "packages/cmk-frontend-vue"
