#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import io
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest
import requests
from assert_build_artifacts import (
    cmk_package_filename,
    Credentials,
    distro_code,
    DockerImage,
    edition_to_registry,
    get_url,
    image_exists_docker_hub,
    image_exists_internal,
    main,
    Registry,
)

from cmk.ccc.version import Edition, Version

EDITIONS_YAML = """
internal_editions:
    - "cloud"
editions:
    pro:
        release: ["debian-12"]
        daily: ["cma-4"]
    cloud:
        release: ["ubuntu-22.04"]
        daily: []
"""

DOWNLOAD_URL = "https://download.checkmk.com/checkmk/2.4.0p1"


class _FakeResponse:
    def __init__(self, status_code: int, payload: object = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._payload = payload
        self.content = content
        self.raw = io.BytesIO(content)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if not self.ok:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass


class _FakeSession:
    """Answers registry tag listings; pages keyed by URL."""

    pages: dict[str, _FakeResponse] = {}

    def __init__(self) -> None:
        self.auth: tuple[str, str] | None = None

    def get(self, url: str, **_kwargs: object) -> _FakeResponse:
        return self.pages.get(url, _FakeResponse(404))


class _FakeDownloadServer:
    """Serves artifacts by name; every file's hash file matches unless listed as corrupt."""

    def __init__(self, missing: Iterable[str] = (), corrupt: Iterable[str] = ()) -> None:
        self.missing = set(missing)
        self.corrupt = set(corrupt)

    @staticmethod
    def _content(filename: str) -> bytes:
        return f"content of {filename}".encode()

    def head(self, url: str, **_kwargs: object) -> _FakeResponse:
        return _FakeResponse(404 if url.rsplit("/", 1)[1] in self.missing else 200)

    def get(self, url: str, **_kwargs: object) -> _FakeResponse:
        filename = url.rsplit("/", 1)[1]
        if filename in self.missing:
            return _FakeResponse(404)
        if not filename.endswith(".hash"):
            return _FakeResponse(200, content=self._content(filename))
        artifact = filename.removesuffix(".hash")
        digest = hashlib.sha256(
            b"corrupt" if artifact in self.corrupt else self._content(artifact)
        ).hexdigest()
        return _FakeResponse(200, content=f"{digest}  {artifact}\n".encode())


@pytest.fixture(name="editions_file")
def fixture_editions_file(tmp_path: Path) -> Path:
    editions_file = tmp_path / "editions.yml"
    editions_file.write_text(EDITIONS_YAML)
    return editions_file


@pytest.fixture(name="credentials_file")
def fixture_credentials_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cmk-credentials").write_text("user:secret\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("NEXUS_USER", "nexus-user")
    monkeypatch.setenv("NEXUS_PASSWORD", "nexus-secret")


@pytest.fixture(name="registries_with_images")
def fixture_registries_with_images(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _FakeSession,
        "pages",
        {
            "https://hub.docker.com/v2/namespaces/checkmk/repositories/check-mk-pro/tags?page_size=100": _FakeResponse(
                200, {"results": [{"name": "2.4.0p1"}], "next": None}
            ),
            "https://artifacts.lan.tribe29.com:4000/v2/check-mk-cloud/tags/list": _FakeResponse(
                200, {"tags": ["2.4.0p1"]}
            ),
            "https://hub.docker.com/v2/repositories/checkmk/check-mk-relay/tags/2.4.0p1/": _FakeResponse(
                200
            ),
        },
    )
    monkeypatch.setattr(requests, "Session", _FakeSession)


def _install_download_server(
    monkeypatch: pytest.MonkeyPatch, server: _FakeDownloadServer, relay_present: bool = True
) -> None:
    monkeypatch.setattr(requests, "head", server.head)

    def get(url: str, **kwargs: object) -> _FakeResponse:
        if "hub.docker.com" in url:
            return _FakeResponse(200 if relay_present else 404)
        return server.get(url, **kwargs)

    monkeypatch.setattr(requests, "get", get)


def _run(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["assert_build_artifacts.py", *argv])
    main()


@pytest.mark.usefixtures("credentials_file", "registries_with_images")
def test_release_with_all_artifacts_reports_no_errors(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_download_server(
        monkeypatch,
        _FakeDownloadServer(
            missing={
                "check-mk-cloud-2.4.0p1.tar.gz",
                "check-mk-cloud-2.4.0p1.tar.gz.hash",
                "check-mk-cloud-2.4.0p1_0.ubuntu-22.04_amd64.deb",
                "check-mk-cloud-2.4.0p1_0.ubuntu-22.04_amd64.deb.hash",
                "check-mk-cloud-2.4.0p1-bill-of-materials.json",
                "check-mk-cloud-2.4.0p1-bill-of-materials.json.hash",
                "check-mk-cloud-2.4.0p1-bill-of-materials.csv",
                "check-mk-cloud-2.4.0p1-bill-of-materials.csv.hash",
                "check-mk-cloud-docker-2.4.0p1.tar.gz",
                "check-mk-cloud-docker-2.4.0p1.tar.gz.hash",
            }
        ),
    )

    _run(
        ["--editions_file", str(editions_file), "assert_build_artifacts", "--version", "2.4.0p1"],
        monkeypatch,
    )

    out = capsys.readouterr().out
    assert (
        f"Checking for {DOWNLOAD_URL}/check-mk-pro-2.4.0p1_0.debian-12_amd64.deb... AVAILABLE"
        in out
    )
    assert f"Checking for {DOWNLOAD_URL}/check-mk-cloud-2.4.0p1.tar.gz... MISSING" in out
    assert "ARTIFACTS_ERRORS:  0" in out


@pytest.mark.usefixtures("credentials_file", "registries_with_images")
def test_missing_public_and_present_internal_artifacts_are_errors(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_download_server(
        monkeypatch,
        _FakeDownloadServer(
            missing={"check-mk-pro-2.4.0p1.tar.gz"},
            corrupt={"check-mk-pro-2.4.0p1-bill-of-materials.csv"},
        ),
    )

    with pytest.raises(RuntimeError) as excinfo:
        _run(
            [
                "--editions_file",
                str(editions_file),
                "--skip_docker",
                "assert_build_artifacts",
                "--version",
                "2.4.0p1",
                "--use_case",
                "daily",
            ],
            monkeypatch,
        )

    message = str(excinfo.value)
    assert "ARTIFACT_MISSING: check-mk-pro-2.4.0p1.tar.gz should be available" in message
    assert "ARTIFACT_PRESENT: check-mk-cloud-2.4.0p1.tar.gz should not be available" in message
    assert "Downloading file failed: HTTP 404" in message, (
        "the hash check of the missing tarball fails as well"
    )
    assert (
        f"File's sha256 sum does not match the hash file {DOWNLOAD_URL}/check-mk-pro-2.4.0p1-bill-of-materials.csv"
        in message
    )


@pytest.mark.usefixtures("credentials_file", "registries_with_images")
def test_missing_relay_image_exits_with_dedicated_code(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_download_server(
        monkeypatch,
        _FakeDownloadServer(missing={"check-mk-pro-2.4.0p1.tar.gz"}),
        relay_present=False,
    )

    with pytest.raises(SystemExit) as excinfo:
        _run(
            [
                "--editions_file",
                str(editions_file),
                "--skip_docker",
                "assert_build_artifacts",
                "--version",
                "2.4.0p1",
            ],
            monkeypatch,
        )
    assert excinfo.value.code == 2

    assert "Relay image checkmk/check-mk-relay:2.4.0p1 not found on Docker Hub!" in (
        capsys.readouterr().err
    )


@pytest.mark.usefixtures("credentials_file")
def test_missing_docker_images_are_errors(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_download_server(monkeypatch, _FakeDownloadServer())
    monkeypatch.setattr(
        _FakeSession,
        "pages",
        {
            "https://hub.docker.com/v2/namespaces/checkmk/repositories/check-mk-pro/tags?page_size=100": _FakeResponse(
                200, {"results": [{"name": "2.4.0"}], "next": None}
            ),
            "https://artifacts.lan.tribe29.com:4000/v2/check-mk-cloud/tags/list": _FakeResponse(
                200, {"tags": []}
            ),
        },
    )
    monkeypatch.setattr(requests, "Session", _FakeSession)

    with pytest.raises(RuntimeError) as excinfo:
        _run(
            [
                "--editions_file",
                str(editions_file),
                "--skip_relay",
                "assert_build_artifacts",
                "--version",
                "2.4.0p1",
            ],
            monkeypatch,
        )

    message = str(excinfo.value)
    assert "DockerImage(image_name='checkmk/check-mk-pro', tag='2.4.0p1') not found!" in message
    assert "DockerImage(image_name='check-mk-cloud', tag='2.4.0p1') not found!" in message


def test_dump_meta_artifacts_mapping_maps_branch_latest_names_to_version(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _run(
        [
            "--editions_file",
            str(editions_file),
            "dump_meta_artifacts_mapping",
            "--version",
            "2.4.0p1",
        ],
        monkeypatch,
    )

    assert json.loads(capsys.readouterr().out) == {
        "check-mk-pro-2.4.0-latest-bill-of-materials.json": "check-mk-pro-2.4.0p1-bill-of-materials.json",
        "check-mk-pro-2.4.0-latest-bill-of-materials.csv": "check-mk-pro-2.4.0p1-bill-of-materials.csv",
        "check-mk-relay-2.4.0-latest-bill-of-materials.json": "check-mk-relay-2.4.0p1-bill-of-materials.json",
    }


def test_dump_meta_artifacts_mapping_version_agnostic_uses_plain_latest(
    editions_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _run(
        [
            "--editions_file",
            str(editions_file),
            "dump_meta_artifacts_mapping",
            "--version",
            "2.4.0p1",
            "--version_agnostic",
        ],
        monkeypatch,
    )

    mapping = json.loads(capsys.readouterr().out)
    assert set(mapping) == {
        "check-mk-pro-latest-bill-of-materials.json",
        "check-mk-pro-latest-bill-of-materials.csv",
        "check-mk-relay-latest-bill-of-materials.json",
    }


def test_release_candidates_are_looked_up_on_the_test_build_server() -> None:
    assert get_url(Version.from_str("2.4.0p1-rc3")) == (
        "https://tstbuilds-artifacts.lan.tribe29.com/2.4.0p1-rc3"
    )


def test_docker_image_round_trips_through_its_full_name() -> None:
    image = DockerImage.from_str("checkmk/check-mk-pro:2.4.0p1")

    assert image == DockerImage(image_name="checkmk/check-mk-pro", tag="2.4.0p1")
    assert image.full_name() == "checkmk/check-mk-pro:2.4.0p1"


@pytest.mark.parametrize(
    "distro, expected",
    [
        pytest.param("cma-4", "cma-4", id="appliance has no distro file"),
        pytest.param("jammy", "jammy", id="already a codename"),
    ],
)
def test_distro_code_passes_through_values_without_distro_file(distro: str, expected: str) -> None:
    assert distro_code(distro) == expected


@pytest.mark.parametrize(
    "distro, expected",
    [
        pytest.param("sles-15sp7", "check-mk-pro-2.4.0p1-sles-15sp7-38.x86_64.rpm", id="sles rpm"),
        pytest.param("el9", "check-mk-pro-2.4.0p1-el9-38.x86_64.rpm", id="enterprise linux rpm"),
        pytest.param("cma-4", "check-mk-pro-2.4.0p1-4-x86_64.cma", id="appliance"),
        pytest.param("jammy", "check-mk-pro-2.4.0p1_0.jammy_amd64.deb", id="debian package"),
    ],
)
def test_cmk_package_filename_follows_distro_family(distro: str, expected: str) -> None:
    assert cmk_package_filename(Edition.PRO, distro, "2.4.0p1-rc2") == expected


def test_edition_without_registry_is_rejected() -> None:
    registry = Registry(
        editions=["pro"],
        url="https://example.com",
        credentials=Credentials("u", "p"),
        image_exists=image_exists_internal,
    )

    with pytest.raises(RuntimeError, match="Cannot determine registry for edition: cloud"):
        edition_to_registry("cloud", [registry])


def test_docker_hub_lookup_follows_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    first = (
        "https://hub.docker.com/v2/namespaces/checkmk/repositories/check-mk-pro/tags?page_size=100"
    )
    monkeypatch.setattr(
        _FakeSession,
        "pages",
        {
            first: _FakeResponse(200, {"results": [{"name": "2.4.0"}], "next": f"{first}&page=2"}),
            f"{first}&page=2": _FakeResponse(200, {"results": [{"name": "2.4.0p1"}]}),
        },
    )

    assert image_exists_docker_hub(
        "https://hub.docker.com/v2",
        "2.4.0p1",
        DockerImage("checkmk/check-mk-pro", "2.4.0p1"),
        _FakeSession(),  # type: ignore[arg-type]
    )


def test_registry_communication_failure_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_FakeSession, "pages", {})

    with pytest.raises(RuntimeError, match="HTTP status 404"):
        image_exists_internal(
            "https://nexus/v2",
            "2.4.0p1",
            DockerImage("check-mk-cloud", "2.4.0p1"),
            _FakeSession(),  # type: ignore[arg-type]
        )
