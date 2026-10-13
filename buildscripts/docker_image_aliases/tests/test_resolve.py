#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

import pytest
import resolve
from resolve import (
    basic_auth,
    credentials_from_docker_config,
    credentials_from_environment,
    credentials_from_netrc,
    keep_repo_tag_alive,
    main,
    split_repo_tag,
)

ALIAS = "IMAGE_TEST_BASE"
IMAGE_ID = "artifacts.lan.tribe29.com:4000/ubuntu@sha256:0123456789abcdef"
REPO_TAG = "artifacts.lan.tribe29.com:4000/ubuntu:22.04-image-alias-master-abc1234"


@pytest.fixture(name="alias_dir")
def fixture_alias_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An image alias next to a fake resolve.py, as register.py would have created it"""
    alias_dir = tmp_path / "aliases" / ALIAS
    alias_dir.mkdir(parents=True)
    (alias_dir / "Dockerfile").write_text(f"# created by register.py\nFROM {IMAGE_ID}\n")
    (alias_dir / "meta.yml").write_text(f"source: ubuntu:22.04\ntag: {REPO_TAG}\n")
    monkeypatch.setattr(resolve, "__file__", str(tmp_path / "aliases" / "resolve.py"))
    return alias_dir


def _run(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["resolve.py", *argv])
    main()


@pytest.fixture(name="no_credentials")
def fixture_no_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXUS_USERNAME", raising=False)
    monkeypatch.delenv("NEXUS_PASSWORD", raising=False)
    monkeypatch.delenv("DOCKER_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))


class _FakeRegistry:
    """Records manifest requests instead of talking to Nexus."""

    def __init__(self) -> None:
        self.requests: list[urllib.request.Request] = []

    def urlopen(self, request: urllib.request.Request, **_kwargs: object) -> _FakeRegistry:
        self.requests.append(request)
        return self

    def __enter__(self) -> _FakeRegistry:
        return self

    def __exit__(self, *_exc: object) -> None:
        pass

    def read(self) -> bytes:
        return b"{}"


@pytest.mark.usefixtures("no_credentials", "alias_dir")
def test_alias_resolves_to_image_of_its_dockerfile_from_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = _FakeRegistry()
    monkeypatch.setattr(urllib.request, "urlopen", registry.urlopen)

    _run([ALIAS, "--no-docker"], monkeypatch)

    assert capsys.readouterr().out.strip() == IMAGE_ID


@pytest.mark.usefixtures("no_credentials", "alias_dir")
def test_resolving_refreshes_the_repo_tag_on_the_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _FakeRegistry()
    monkeypatch.setattr(urllib.request, "urlopen", registry.urlopen)

    _run([ALIAS, "--no-docker"], monkeypatch)

    (request,) = registry.requests
    assert request.full_url == (
        "https://artifacts.lan.tribe29.com:4000/v2/ubuntu/manifests/22.04-image-alias-master-abc1234"
    )
    assert "application/vnd.oci.image.index.v1+json" in request.get_header("Accept", "")
    assert not request.has_header("Authorization")


@pytest.mark.usefixtures("alias_dir")
def test_check_prints_the_repo_tag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _run([ALIAS, "--check", "--no-docker"], monkeypatch)

    assert capsys.readouterr().out.strip() == f"Resolved repo tag: {REPO_TAG}"


@pytest.mark.usefixtures("alias_dir")
def test_unknown_alias_fails_loudly(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        _run(["IMAGE_DOES_NOT_EXIST", "--no-docker"], monkeypatch)
    assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert captured.out.strip() == "INVALID_IMAGE_ID"
    assert "could not be resolved" in captured.err


def test_repo_tag_is_split_into_registry_image_and_tag() -> None:
    assert split_repo_tag("artifacts.lan.tribe29.com:4000/ubuntu:22.04-image-alias") == (
        "artifacts.lan.tribe29.com:4000",
        "ubuntu",
        "22.04-image-alias",
    )


@pytest.mark.parametrize(
    "repo_tag",
    [
        pytest.param("ubuntu:22.04", id="no registry"),
        pytest.param("registry/ubuntu:22.04", id="registry without domain"),
        pytest.param("registry.example.com/ubuntu", id="no tag"),
    ],
)
def test_incomplete_repo_tags_are_rejected(repo_tag: str) -> None:
    with pytest.raises(ValueError, match="not a registry reference"):
        split_repo_tag(repo_tag)


def test_environment_credentials_are_base64_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_USERNAME", "jenkins")
    monkeypatch.setenv("NEXUS_PASSWORD", "s3cret")

    assert credentials_from_environment() == base64.b64encode(b"jenkins:s3cret").decode()


def test_environment_credentials_need_both_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_USERNAME", "jenkins")
    monkeypatch.delenv("NEXUS_PASSWORD", raising=False)

    assert credentials_from_environment() is None


def test_docker_config_credentials_prefer_docker_config_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".docker").mkdir()
    (tmp_path / ".docker/config.json").write_text(
        json.dumps({"auths": {"reg.example.com": {"auth": "home"}}})
    )
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom/config.json").write_text(
        json.dumps({"auths": {"reg.example.com": {"auth": "custom"}}})
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOCKER_CONFIG", str(tmp_path / "custom"))

    assert credentials_from_docker_config("reg.example.com") == "custom"


def test_docker_config_without_entry_yields_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".docker").mkdir()
    (tmp_path / ".docker/config.json").write_text(
        json.dumps({"auths": {"other.example.com": {"auth": "x"}}})
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DOCKER_CONFIG", raising=False)

    assert credentials_from_docker_config("reg.example.com") is None


def test_malformed_docker_config_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".docker").mkdir()
    (tmp_path / ".docker/config.json").write_text("{not json")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DOCKER_CONFIG", raising=False)

    assert credentials_from_docker_config("reg.example.com") is None


def test_netrc_credentials_match_the_registry_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text("machine reg.example.com login alice password wonderland\n")
    netrc_file.chmod(0o600)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NETRC", raising=False)

    assert credentials_from_netrc("reg.example.com:4000") == (
        base64.b64encode(b"alice:wonderland").decode()
    )


def test_netrc_without_matching_machine_yields_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text("machine other.example.com login bob password x\n")
    netrc_file.chmod(0o600)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NETRC", raising=False)

    assert credentials_from_netrc("reg.example.com") is None


def test_missing_netrc_yields_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NETRC", raising=False)

    assert credentials_from_netrc("reg.example.com") is None


@pytest.mark.usefixtures("no_credentials")
def test_basic_auth_falls_back_through_all_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text("machine reg.example.com login alice password wonderland\n")
    netrc_file.chmod(0o600)
    monkeypatch.delenv("NETRC", raising=False)

    assert basic_auth("reg.example.com") == base64.b64encode(b"alice:wonderland").decode()


def test_keep_alive_sends_credentials_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _FakeRegistry()
    monkeypatch.setattr(urllib.request, "urlopen", registry.urlopen)
    monkeypatch.setenv("NEXUS_USERNAME", "jenkins")
    monkeypatch.setenv("NEXUS_PASSWORD", "s3cret")

    keep_repo_tag_alive("reg.example.com:4000/ubuntu:22.04")

    (request,) = registry.requests
    assert request.get_header("Authorization") == (
        f"Basic {base64.b64encode(b'jenkins:s3cret').decode()}"
    )


@pytest.mark.usefixtures("no_credentials")
def test_keep_alive_failure_only_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def urlopen(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    keep_repo_tag_alive("reg.example.com:4000/ubuntu:22.04")

    assert (
        "WARNING: could not refresh 'reg.example.com:4000/ubuntu:22.04'" in capsys.readouterr().err
    )


@pytest.mark.usefixtures("no_credentials")
def test_keep_alive_with_invalid_tag_only_warns(capsys: pytest.CaptureFixture[str]) -> None:
    keep_repo_tag_alive("ubuntu")

    assert "not a registry reference" in capsys.readouterr().err
