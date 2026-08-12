# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for the deploy-server Bazel command composition."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cmk.dev_deploy.core.bazel import (
    bazel_command,
    deploy_output_base,
    ensure_bazel_wrapper,
    OUTPUT_BASE_ENV,
    request_shared_server,
    SHARED_SERVER_ENV,
    use_shared_server,
)
from cmk.dev_deploy.errors import DeployError


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(OUTPUT_BASE_ENV, raising=False)
    monkeypatch.delenv(SHARED_SERVER_ENV, raising=False)


class TestDeployOutputBase:
    def test_derived_from_xdg_cache_and_repo_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        output_base = deploy_output_base(tmp_path / "checkout")
        assert output_base.parent == tmp_path / "cmk-dev-deploy" / "bazel"
        assert len(output_base.name) == 32  # md5 hex digest of the checkout path

    def test_stable_per_checkout(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        first = deploy_output_base(tmp_path / "checkout")
        assert first == deploy_output_base(tmp_path / "checkout")
        assert first != deploy_output_base(tmp_path / "other-checkout")

    def test_env_override_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(OUTPUT_BASE_ENV, "/custom/output-base")
        assert deploy_output_base(tmp_path) == Path("/custom/output-base")


class TestBazelCommand:
    def test_build_gets_output_base_and_symlink_suppression(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(OUTPUT_BASE_ENV, "/ob")
        assert bazel_command(["build", "--cmk_edition=pro", "//pkg:t"], tmp_path) == [
            "bazel",
            "--output_base=/ob",
            "--host_jvm_args=-Xmx3g",
            "build",
            "--symlink_prefix=/",
            "--cmk_edition=pro",
            "//pkg:t",
        ]

    def test_run_suppresses_symlinks_before_target_args(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(OUTPUT_BASE_ENV, "/ob")
        cmd = bazel_command(["run", "//:deploy-python", "--", "/omd/sites/x"], tmp_path)
        assert cmd.index("--symlink_prefix=/") < cmd.index("--")

    @pytest.mark.parametrize("command", ["query", "cquery", "info"])
    def test_non_building_commands_touch_no_symlinks(
        self, command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(OUTPUT_BASE_ENV, "/ob")
        cmd = bazel_command([command, "somearg"], tmp_path)
        assert "--output_base=/ob" in cmd
        assert "--symlink_prefix=/" not in cmd

    def test_shared_mode_returns_plain_argv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(SHARED_SERVER_ENV, "1")
        assert bazel_command(["build", "//pkg:t"], tmp_path) == ["bazel", "build", "//pkg:t"]

    def test_shared_env_zero_means_isolated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(SHARED_SERVER_ENV, "0")
        assert not use_shared_server()

    def test_request_shared_server(self) -> None:
        assert not use_shared_server()
        request_shared_server()
        assert use_shared_server()


class TestEnsureBazelWrapper:
    def test_shared_mode_needs_no_wrapper(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(SHARED_SERVER_ENV, "1")
        assert ensure_bazel_wrapper(Path("/repo")) is None

    def test_writes_executable_shim(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        monkeypatch.setenv(OUTPUT_BASE_ENV, "/ob")
        monkeypatch.setattr(
            "cmk.dev_deploy.core.bazel.shutil.which", lambda _name: "/usr/bin/bazel"
        )
        wrapper = ensure_bazel_wrapper(tmp_path / "checkout")
        assert wrapper is not None
        assert os.access(wrapper, os.X_OK)
        content = wrapper.read_text()
        assert content.startswith("#!/bin/sh\n")
        assert 'exec "/usr/bin/bazel" "--output_base=/ob"' in content
        assert content.rstrip().endswith('"$@"')

    def test_regenerated_on_every_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        monkeypatch.setattr("cmk.dev_deploy.core.bazel.shutil.which", lambda _name: "/old/bazel")
        first = ensure_bazel_wrapper(tmp_path / "checkout")
        monkeypatch.setattr("cmk.dev_deploy.core.bazel.shutil.which", lambda _name: "/new/bazel")
        second = ensure_bazel_wrapper(tmp_path / "checkout")
        assert first == second
        assert second is not None
        assert '"/new/bazel"' in second.read_text()

    def test_missing_bazel_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cmk.dev_deploy.core.bazel.shutil.which", lambda _name: None)
        with pytest.raises(DeployError, match="bazel not found"):
            ensure_bazel_wrapper(tmp_path / "checkout")
