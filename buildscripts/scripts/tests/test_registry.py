#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import docker.client
import docker.errors
import pytest
import requests

from buildscripts.scripts.lib.registry import (
    DockerImage,
    edition_to_registry,
    get_default_registries,
    Registry,
)

DOCKER_HUB_EDITIONS = ["community", "ultimate", "ultimatemt", "pro"]


class _FakeImage:
    def __init__(self, tags: list[str]) -> None:
        self.tags = tags

    def tag(self, repository: str, tag: str) -> bool:
        self.tags.append(f"{repository}:{tag}")
        return True

    def reload(self) -> None:
        pass


class _FakeImages:
    def __init__(self) -> None:
        self.remote: dict[str, _FakeImage] = {}
        self.local: dict[str, _FakeImage] = {}
        self.pushed: list[str] = []

    def pull(self, name: str, tag: str) -> _FakeImage:
        return self.remote[f"{name}:{tag}"]

    def get_registry_data(self, name: str) -> _FakeImage:
        if name not in self.remote:
            raise docker.errors.NotFound(f"{name} not found")
        return self.remote[name]

    def get(self, name: str) -> _FakeImage:
        return self.local[name]

    def push(self, repository: str, tag: str, **_kwargs: object) -> Iterator[dict[str, str]]:
        self.pushed.append(f"{repository}:{tag}")
        yield {"status": "Pushed"}


class _FakeDockerClient:
    def __init__(self) -> None:
        self.images = _FakeImages()


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: object = None,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text
        self.content = text.encode()

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self) -> object:
        return self._payload


@pytest.fixture(name="docker_client")
def fixture_docker_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _FakeDockerClient:
    client = _FakeDockerClient()
    monkeypatch.setattr(docker.client, "from_env", lambda **_kwargs: client)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cmk-credentials").write_text("hub-user:hub-secret\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("NEXUS_USER", "nexus-user")
    monkeypatch.setenv("NEXUS_PASSWORD", "nexus-secret")
    return client


@pytest.mark.usefixtures("docker_client")
def test_default_registries_cover_docker_hub_and_nexus() -> None:
    hub, nexus = get_default_registries()

    assert hub.url == "https://hub.docker.com/"
    assert nexus.url == "https://artifacts.lan.tribe29.com:4000"
    assert nexus.credentials.username == "nexus-user"


@pytest.mark.usefixtures("docker_client")
def test_edition_is_mapped_to_its_registry() -> None:
    registries = get_default_registries()

    assert edition_to_registry("cloud", registries) is registries[1]


@pytest.mark.usefixtures("docker_client")
def test_edition_without_registry_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Cannot determine registry for edition: saas"):
        edition_to_registry("saas", get_default_registries())


@pytest.mark.usefixtures("docker_client")
def test_unknown_edition_set_has_no_registry() -> None:
    with pytest.raises(RuntimeError, match="Cannnot match editions to registry"):
        Registry(editions=["pro"])


@pytest.mark.usefixtures("docker_client")
def test_registry_client_timeout_is_honoured() -> None:
    assert Registry(editions=DOCKER_HUB_EDITIONS, timeout=42).timeout == 42


def test_docker_image_parses_its_full_name() -> None:
    assert DockerImage.from_str("checkmk/check-mk-pro:2.3.0p1").full_name() == (
        "checkmk/check-mk-pro:2.3.0p1"
    )


def test_docker_hub_image_exists_when_registry_has_data(docker_client: _FakeDockerClient) -> None:
    docker_client.images.remote["checkmk/check-mk-pro:2.3.0p1"] = _FakeImage([])
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    assert registry.image_exists(DockerImage("checkmk/check-mk-pro", "2.3.0p1"), "pro")
    assert not registry.image_exists(DockerImage("checkmk/check-mk-pro", "2.3.0p2"), "pro")


@pytest.mark.usefixtures("docker_client")
def test_nexus_image_exists_when_tag_is_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        requests,
        "get",
        lambda _url, **_kwargs: _FakeResponse(200, {"tags": ["2.3.0p1", "2.3.0-latest"]}),
    )
    registry = Registry(editions=["cloud"])

    assert registry.image_exists(DockerImage("check-mk-cloud", "2.3.0p1"), "cloud")
    assert not registry.image_exists(DockerImage("check-mk-cloud", "2.3.0p9"), "cloud")


@pytest.mark.usefixtures("docker_client")
def test_nexus_communication_failure_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda _url, **_kwargs: _FakeResponse(503, text="down"))
    registry = Registry(editions=["cloud"])

    with pytest.raises(RuntimeError, match="HTTP status 503- down"):
        registry.image_exists(DockerImage("check-mk-cloud", "2.3.0p1"), "cloud")


@pytest.mark.parametrize(
    "tags, expected",
    [
        pytest.param(["checkmk/check-mk-pro:2.3.0-latest"], True, id="branch latest"),
        pytest.param(["checkmk/check-mk-pro:2.3.0-daily"], True, id="branch daily"),
        pytest.param(["checkmk/check-mk-pro:2.3.0p1"], False, id="plain release"),
    ],
)
def test_image_is_latest_when_a_latest_style_tag_points_to_it(
    docker_client: _FakeDockerClient, tags: list[str], expected: bool
) -> None:
    docker_client.images.remote["checkmk/check-mk-pro:2.3.0p1"] = _FakeImage(tags)
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    assert registry.is_latest_image(DockerImage("checkmk/check-mk-pro", "2.3.0p1")) is expected


@pytest.mark.usefixtures("docker_client")
def test_docker_hub_image_listing_follows_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    first = (
        "https://hub.docker.com//v2/namespaces/checkmk/repositories/check-mk-pro/tags?page_size=100"
    )
    pages = {
        first: _FakeResponse(200, {"results": [{"name": "2.3.0p1"}], "next": f"{first}&page=2"}),
        f"{first}&page=2": _FakeResponse(200, {"results": [{"name": "2.3.0p2"}], "next": None}),
    }

    class _Session:
        auth: tuple[str, str] | None = None

        def get(self, url: str, **_kwargs: object) -> _FakeResponse:
            return pages[url]

    monkeypatch.setattr(requests, "Session", _Session)
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    assert list(registry.list_images("checkmk/check-mk-pro")) == [
        DockerImage("checkmk/check-mk-pro", "2.3.0p1"),
        DockerImage("checkmk/check-mk-pro", "2.3.0p2"),
    ]


@pytest.mark.usefixtures("docker_client")
def test_docker_hub_image_listing_stops_on_failed_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class _Session:
        auth: tuple[str, str] | None = None

        def get(self, *_args: object, **_kwargs: object) -> _FakeResponse:
            return _FakeResponse(500)

    monkeypatch.setattr(requests, "Session", _Session)
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    assert list(registry.list_images("checkmk/check-mk-pro")) == []
    assert "failed: 500" in capsys.readouterr().err


@pytest.mark.usefixtures("docker_client")
def test_nexus_image_listing_uses_tag_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        requests, "get", lambda _url, **_kwargs: _FakeResponse(200, {"tags": ["2.3.0p1"]})
    )
    registry = Registry(editions=["cloud"])

    assert list(registry.list_images("check-mk-cloud")) == [
        DockerImage("check-mk-cloud", "2.3.0p1")
    ]


@pytest.mark.usefixtures("docker_client")
def test_previous_release_lookup_needs_a_release_suffix() -> None:
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    with pytest.raises(ValueError, match="misses build information"):
        registry.get_previous_release_tag(DockerImage("checkmk/check-mk-pro", "2.3.0"), "pro")


@pytest.mark.usefixtures("docker_client")
def test_previous_release_lookup_returns_first_existing_candidate() -> None:
    registry = Registry(editions=DOCKER_HUB_EDITIONS)
    probed: list[str] = []

    def image_exists(image: DockerImage, _edition: str) -> bool:
        probed.append(image.tag)
        return len(probed) == 3

    registry.image_exists = image_exists

    previous = registry.get_previous_release_tag(
        DockerImage("checkmk/check-mk-pro", "2.3.0p24"), "pro"
    )

    assert probed == ["2.3.0p23", "2.3.0p22", "2.3.0p21"]
    assert previous == "2.3.0p21"


@pytest.mark.usefixtures("docker_client")
def test_previous_daily_lookup_probes_earlier_dates() -> None:
    registry = Registry(editions=DOCKER_HUB_EDITIONS)
    probed: list[str] = []

    def image_exists(image: DockerImage, _edition: str) -> bool:
        probed.append(image.tag)
        return True

    registry.image_exists = image_exists

    registry.get_previous_release_tag(
        DockerImage("checkmk/check-mk-pro", "2.3.0-2024.03.01"), "pro"
    )

    assert probed == ["2.3.0-2024.02.29"]


@pytest.mark.usefixtures("docker_client")
def test_previous_release_lookup_gives_up_after_ten_attempts() -> None:
    registry = Registry(editions=DOCKER_HUB_EDITIONS)
    registry.image_exists = lambda _image, _edition: False

    with pytest.raises(RuntimeError, match="after 10 attempts"):
        registry.get_previous_release_tag(DockerImage("checkmk/check-mk-pro", "2.3.0p24"), "pro")


def test_tagging_pushes_the_new_tag(docker_client: _FakeDockerClient) -> None:
    image = _FakeImage(["hub.docker.com/checkmk/check-mk-pro:2.3.0p23"])
    docker_client.images.local["hub.docker.com/checkmk/check-mk-pro:2.3.0p23"] = image
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    registry.tag("checkmk/check-mk-pro:2.3.0p23", "2.3.0-latest")

    assert "hub.docker.com/checkmk/check-mk-pro:2.3.0-latest" in image.tags
    assert docker_client.images.pushed == ["hub.docker.com/checkmk/check-mk-pro:2.3.0-latest"]


@pytest.mark.usefixtures("docker_client")
def test_tagging_rejects_empty_tag() -> None:
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    with pytest.raises(ValueError, match="Please supply a tag"):
        registry.tag("checkmk/check-mk-pro:2.3.0p23", "  ")


@pytest.mark.usefixtures("docker_client")
def test_docker_hub_deletion_uses_a_login_token(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(
        requests, "post", lambda _url, **_kwargs: _FakeResponse(200, {"token": "jwt-token"})
    )

    def delete(url: str, headers: dict[str, str], **_kwargs: object) -> _FakeResponse:
        deleted.append((url, headers))
        return _FakeResponse(204)

    monkeypatch.setattr(requests, "delete", delete)
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    registry.delete_image(DockerImage("checkmk/check-mk-pro", "2.3.0p24"))

    assert deleted == [
        (
            "https://hub.docker.com//v2/repositories/checkmk/check-mk-pro/tags/2.3.0p24",
            {"Content-type": "application/json", "Authorization": "JWT jwt-token"},
        )
    ]


@pytest.mark.usefixtures("docker_client")
def test_nexus_deletion_resolves_the_manifest_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []
    monkeypatch.setattr(
        requests,
        "get",
        lambda _url, **_kwargs: _FakeResponse(200, headers={"Docker-Content-Digest": "sha256:abc"}),
    )

    def delete(url: str, **_kwargs: object) -> _FakeResponse:
        deleted.append(url)
        return _FakeResponse(202)

    monkeypatch.setattr(requests, "delete", delete)
    registry = Registry(editions=["cloud"])

    registry.delete_image(DockerImage("check-mk-cloud", "2.3.0p24"))

    assert deleted == [
        "https://artifacts.lan.tribe29.com:4000/v2/check-mk-cloud/manifests/sha256:abc"
    ]


@pytest.mark.usefixtures("docker_client")
def test_nexus_deletion_fails_without_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests, "get", lambda _url, **_kwargs: _FakeResponse(404))
    registry = Registry(editions=["cloud"])

    with pytest.raises(RuntimeError, match="Could not get digest"):
        registry.delete_image(DockerImage("check-mk-cloud", "2.3.0p24"))


@pytest.mark.usefixtures("docker_client")
def test_failed_deletion_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        requests, "post", lambda _url, **_kwargs: _FakeResponse(200, {"token": "t"})
    )
    monkeypatch.setattr(requests, "delete", lambda _url, **_kwargs: _FakeResponse(403))
    registry = Registry(editions=DOCKER_HUB_EDITIONS)

    with pytest.raises(RuntimeError, match="Could not delete image tag"):
        registry.delete_image(DockerImage("checkmk/check-mk-pro", "2.3.0p24"))
