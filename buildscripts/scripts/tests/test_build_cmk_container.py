#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import gzip
import importlib.util
import io
import shutil
import sys
import tarfile
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import ModuleType

import docker
import docker.errors
import pytest


class _FakeImage:
    def __init__(self, tags: list[str]) -> None:
        self.tags = tags

    def tag(self, repository: str, tag: str) -> bool:
        self.tags.append(f"{repository}:{tag}")
        return True

    def reload(self) -> None:
        pass

    def save(self, named: str | bool = False) -> Iterator[bytes]:
        yield f"image {named}".encode()


class _FakeImages:
    def __init__(self) -> None:
        self.images: list[_FakeImage] = []
        self.pushed: list[str] = []
        self.push_errors: set[str] = set()
        self.removed: list[str] = []
        self.loaded: list[bytes] = []
        self.builds: list[dict[str, object]] = []

    def add(self, *tags: str) -> _FakeImage:
        image = _FakeImage(list(tags))
        self.images.append(image)
        return image

    def get(self, name: str) -> _FakeImage:
        for image in self.images:
            if name in image.tags:
                return image
        raise docker.errors.ImageNotFound(f"{name} not found")

    def push(self, repository: str, tag: str, **_kwargs: object) -> Iterator[dict[str, str]]:
        full_name = f"{repository}:{tag}"
        self.pushed.append(full_name)
        yield {"status": "Pushing"}
        if full_name in self.push_errors:
            yield {"error": "denied"}

    def load(self, data: bytes) -> list[_FakeImage]:
        self.loaded.append(data)
        return [self.add()]

    def build(self, **kwargs: object) -> tuple[_FakeImage, list[dict[str, str]]]:
        self.builds.append(kwargs)
        return self.add(str(kwargs["tag"])), [
            {"stream": "Step 1/3\nStep 2/3\n"},
            {"aux": "sha256:abc"},
        ]

    def remove(self, image: str) -> None:
        self.removed.append(image)


class _FakeDockerClient:
    def __init__(self) -> None:
        self.images = _FakeImages()
        self.logins: list[tuple[str, str]] = []

    def login(self, registry: str, username: str, **_kwargs: object) -> None:
        self.logins.append((registry, username))

    def info(self) -> dict[str, str]:
        return {"ServerVersion": "fake"}


@pytest.fixture(name="docker_client")
def fixture_docker_client(monkeypatch: pytest.MonkeyPatch) -> _FakeDockerClient:
    client = _FakeDockerClient()
    monkeypatch.setattr(docker, "from_env", lambda **_kwargs: client)
    return client


@pytest.fixture(name="script")
def fixture_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, docker_client: _FakeDockerClient
) -> ModuleType:
    """The script connects to docker and creates its work dir on import, so it is loaded
    per test with the fake client in place and a fresh working directory."""
    monkeypatch.chdir(tmp_path)
    path = Path(__file__).parent.parent / "build-cmk-container.py"
    spec = importlib.util.spec_from_file_location("build_cmk_container", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.docker_client is docker_client
    return module


def _args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "edition": "pro",
        "branch": "2.4.0",
        "version": "2.4.0p1",
        "set_latest_tag": False,
        "set_branch_latest_tag": False,
        "no_cache": False,
        "image_cmk_base": "base-image:1",
        "verbose": 0,
    }
    return argparse.Namespace(**{**defaults, **overrides})


def test_run_cmd_returns_completed_process(script: ModuleType) -> None:
    assert script.run_cmd(["echo", "hello"]).stdout == "hello\n"


def test_run_cmd_raises_on_failure(script: ModuleType) -> None:
    with pytest.raises(Exception, match="Failed to execute command 'false'"):
        script.run_cmd(["false"])


def test_run_cmd_can_tolerate_failure(script: ModuleType) -> None:
    assert script.run_cmd(["false"], raise_exception=False).returncode == 1


def test_needed_packages_collects_os_packages_lines(script: ModuleType, tmp_path: Path) -> None:
    mk_file = tmp_path / "distro.mk"
    mk_file.write_text(
        "DISTRO_CODE = jammy\nOS_PACKAGES += libcap2 # capabilities\nOS_PACKAGES += curl\n"
    )

    script.needed_packages(str(mk_file), str(tmp_path / "needed"))

    assert (tmp_path / "needed").read_text() == "libcap2 curl"


def test_tagging_adds_versioned_and_daily_tags(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    image = docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    script.docker_tag(_args(), "2.4.0p1", "artifacts.lan.tribe29.com:4000", "")

    assert image.tags == [
        "checkmk/check-mk-pro:2.4.0p1",
        "artifacts.lan.tribe29.com:4000/check-mk-pro:2.4.0p1",
        "artifacts.lan.tribe29.com:4000/check-mk-pro:2.4.0-daily",
    ]


def test_tagging_can_mark_branch_latest_and_latest(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    image = docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    script.docker_tag(
        _args(set_branch_latest_tag=True, set_latest_tag=True), "2.4.0p1", "", "checkmk", "2.4.0p1"
    )

    assert image.tags[1:] == [
        "checkmk/check-mk-pro:2.4.0p1",
        "checkmk/check-mk-pro:2.4.0-latest",
        "checkmk/check-mk-pro:latest",
    ]


@pytest.fixture(name="registry_env")
def fixture_registry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCKER_USERNAME", "hub-user")
    monkeypatch.setenv("DOCKER_PASSPHRASE", "hub-secret")
    monkeypatch.setenv("NEXUS_USERNAME", "nexus-user")
    monkeypatch.setenv("NEXUS_PASSWORD", "nexus-secret")


@pytest.mark.usefixtures("registry_env")
def test_push_logs_in_and_pushes_version_and_daily_tags(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    script.docker_push(
        _args(),
        "2.4.0p1",
        script.RegistryConfig("", "checkmk", "DOCKER_USERNAME", "DOCKER_PASSPHRASE"),
    )

    assert docker_client.logins == [("", "hub-user")]
    assert docker_client.images.pushed == [
        "checkmk/check-mk-pro:2.4.0p1",
        "checkmk/check-mk-pro:2.4.0-daily",
    ]


@pytest.mark.usefixtures("registry_env")
def test_push_of_release_candidate_retags_without_rc_suffix(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    image = docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    script.docker_push(
        _args(set_latest_tag=True, set_branch_latest_tag=True),
        "2.4.0p1-rc2",
        script.RegistryConfig("", "checkmk", "DOCKER_USERNAME", "DOCKER_PASSPHRASE"),
    )

    assert "checkmk/check-mk-pro:2.4.0-latest" in image.tags
    assert docker_client.images.pushed == [
        "checkmk/check-mk-pro:2.4.0p1",
        "checkmk/check-mk-pro:2.4.0-latest",
        "checkmk/check-mk-pro:latest",
    ]


@pytest.mark.usefixtures("registry_env")
def test_push_error_is_raised(script: ModuleType, docker_client: _FakeDockerClient) -> None:
    docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")
    docker_client.images.push_errors.add("checkmk/check-mk-pro:2.4.0p1")

    with pytest.raises(ValueError, match="Some error occurred during upload"):
        script.docker_push(
            _args(),
            "2.4.0p1",
            script.RegistryConfig("", "checkmk", "DOCKER_USERNAME", "DOCKER_PASSPHRASE"),
        )


def test_load_imports_tarball_and_tags_it(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    with gzip.open(Path(script.tmp_path) / "check-mk-pro-docker-2.4.0p1.tar.gz", "wb") as tarball:
        tarball.write(b"image bytes")

    script.docker_load(_args(), "2.4.0p1", "registry:4000", "")

    assert docker_client.images.loaded == [b"image bytes"]
    assert docker_client.images.images[-1].tags == ["registry:4000/check-mk-pro:2.4.0p1"]


def test_local_image_check_reports_presence(
    script: ModuleType, docker_client: _FakeDockerClient
) -> None:
    docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    assert script.check_for_local_image(_args(), "2.4.0p1", "", "checkmk")
    assert not script.check_for_local_image(_args(), "2.4.0p2", "", "checkmk")


def test_build_writes_image_tarball(
    script: ModuleType, docker_client: _FakeDockerClient, tmp_path: Path
) -> None:
    docker_path = tmp_path / "docker_image"
    docker_path.mkdir()

    script.build_tar_gz(_args(no_cache=True), "2.4.0p1", str(docker_path), "checkmk")

    (build,) = docker_client.images.builds
    assert build["buildargs"] == {
        "CMK_VERSION": "2.4.0p1",
        "CMK_EDITION": "pro",
        "IMAGE_CMK_BASE": "base-image:1",
    }
    assert build["nocache"] is True
    with gzip.open(docker_path / "check-mk-pro-docker-2.4.0p1.tar.gz") as tarball:
        assert tarball.read() == b"image checkmk/check-mk-pro:2.4.0p1"


def test_build_of_release_candidate_saves_under_release_tag(
    script: ModuleType, docker_client: _FakeDockerClient, tmp_path: Path
) -> None:
    docker_path = tmp_path / "docker_image"
    docker_path.mkdir()

    script.build_tar_gz(_args(), "2.4.0p1-rc2", str(docker_path), "checkmk")

    with gzip.open(docker_path / "check-mk-pro-docker-2.4.0p1.tar.gz") as tarball:
        assert tarball.read() == b"image checkmk/check-mk-pro:2.4.0p1"
    assert docker_client.images.removed == ["checkmk/check-mk-pro:2.4.0p1"]


def _write_source_artifacts(source_path: Path, architecture: str) -> None:
    source_path.mkdir()
    with tarfile.open(source_path / "check-mk-pro-2.4.0p1.tar.gz", "w:gz") as archive:
        dockerfile = tarfile.TarInfo("check-mk-pro-2.4.0p1/docker_image/Dockerfile")
        content = b"FROM scratch\n"
        dockerfile.size = len(content)
        archive.addfile(dockerfile, io.BytesIO(content))
    (source_path / f"check-mk-pro-2.4.0p1_0.jammy_{architecture}.deb").write_bytes(b"deb")


def test_build_image_prepares_context_and_tags_result(
    script: ModuleType, docker_client: _FakeDockerClient, tmp_path: Path
) -> None:
    if shutil.which("dpkg") is None:
        pytest.skip("build_image determines the architecture via dpkg")
    architecture = script.run_cmd(["dpkg", "--print-architecture"]).stdout.strip()
    source_path = tmp_path / "download"
    _write_source_artifacts(source_path, architecture)
    (tmp_path / "omd/distros").mkdir(parents=True)
    (tmp_path / "omd/distros/UBUNTU_22.04.mk").write_text("OS_PACKAGES += libcap2\n")

    script.build_image(_args(source_path=str(source_path)), "", "checkmk", "2.4.0p1")

    assert (source_path / "check-mk-pro-docker-2.4.0p1.tar.gz").exists()
    docker_path = Path(script.tmp_path) / "check-mk-pro-2.4.0p1/docker_image"
    assert (docker_path / "needed-packages").read_text() == "libcap2"
    assert (docker_path / f"check-mk-pro-2.4.0p1_0.jammy_{architecture}.deb").exists()
    assert docker_client.images.images[-1].tags[-1] == "checkmk/check-mk-pro:2.4.0-daily"


def _run_main(script: ModuleType, argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["build-cmk-container.py", *argv])
    script.main()


def test_main_check_local_passes_for_present_image(
    script: ModuleType,
    docker_client: _FakeDockerClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    docker_client.images.add("artifacts.lan.tribe29.com:4000/check-mk-cloud:2.4.0p1")

    _run_main(
        script,
        [
            "--branch=2.4.0",
            "--edition=cloud",
            "--version=2.4.0p1",
            "--version_rc_aware=2.4.0p1-rc1",
            f"--source_path={tmp_path}/2.4.0p1-rc1",
            "--action=check_local",
            "-vvv",
        ],
        monkeypatch,
    )

    assert "artifacts.lan.tribe29.com:4000/check-mk-cloud:2.4.0p1 locally available" in caplog.text
    assert docker_client.images.loaded == []
    assert docker_client.images.pushed == []


def test_main_check_local_fails_for_missing_image(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(SystemExit, match="Image not found locally"):
        _run_main(
            script,
            [
                "--branch=2.4.0",
                "--edition=pro",
                "--version=2.4.0p1",
                "--version_rc_aware=2.4.0p1",
                f"--source_path={tmp_path}/2.4.0p1",
                "--action=check_local",
            ],
            monkeypatch,
        )


def test_main_load_requires_release_key_when_image_is_missing(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RELEASE_KEY", raising=False)

    with pytest.raises(SystemExit, match="RELEASE_KEY not found"):
        _run_main(
            script,
            [
                "--branch=2.4.0",
                "--edition=ultimate",
                "--version=2.4.0p1",
                "--version_rc_aware=2.4.0p1",
                f"--source_path={tmp_path}/2.4.0p1",
                "--action=load",
            ],
            monkeypatch,
        )


def test_main_load_skips_download_for_present_image(
    script: ModuleType,
    docker_client: _FakeDockerClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_client.images.add("checkmk/check-mk-pro:2.4.0p1")

    _run_main(
        script,
        [
            "--branch=2.4.0",
            "--edition=pro",
            "--version=2.4.0p1",
            "--version_rc_aware=2.4.0p1",
            f"--source_path={tmp_path}/2.4.0p1",
            "--action=load",
        ],
        monkeypatch,
    )

    assert docker_client.images.loaded == []


@pytest.mark.usefixtures("registry_env")
def test_main_push_of_ultimate_targets_both_registries(
    script: ModuleType,
    docker_client: _FakeDockerClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_client.images.add("checkmk/check-mk-ultimate:2.4.0p1")

    _run_main(
        script,
        [
            "--branch=2.4.0",
            "--edition=ultimate",
            "--version=2.4.0p1",
            f"--source_path={tmp_path}/2.4.0p1+meta",
            "--action=push",
            "--set_latest_tag=yes",
        ],
        monkeypatch,
    )

    assert [registry for registry, _user in docker_client.logins] == [
        "",
        "artifacts.lan.tribe29.com:4000",
    ]
    assert "artifacts.lan.tribe29.com:4000/check-mk-ultimate:latest" in docker_client.images.pushed


def test_cleanup_removes_the_working_directory(script: ModuleType) -> None:
    assert Path(script.tmp_path).exists()

    script.cleanup()

    assert not Path(script.tmp_path).exists()
