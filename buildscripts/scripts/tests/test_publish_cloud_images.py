#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import json
import sys
from collections.abc import Sequence
from types import SimpleNamespace

import pytest
from azure.mgmt.compute.models import GalleryImageVersion
from publish_cloud_images import (
    AWSPublisher,
    AzurePublisher,
    CloudPublisher,
    ensure_using_official_release,
    parse_arguments,
)

from cmk.ccc.version import Version

VERSION = Version.from_str("2.4.0p5")


def _parse(argv: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setattr(sys, "argv", ["publish_cloud_images.py", *argv])
    return parse_arguments()


COMMON_ARGS = ["--new-version", "2.4.0p5", "--build-tag", "job-1", "--image-name", "cmk-image"]


def test_aws_arguments_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    args = _parse(
        [
            "--cloud-type",
            "aws",
            *COMMON_ARGS,
            "--marketplace-scanner-arn",
            "arn:scanner",
            "--product-id",
            "prod-1",
        ],
        monkeypatch,
    )

    assert vars(args) == {
        "cloud_type": "aws",
        "new_version": "2.4.0p5",
        "build_tag": "job-1",
        "image_name": "cmk-image",
        "marketplace_scanner_arn": "arn:scanner",
        "product_id": "prod-1",
        "azure_subscription_id": None,
        "azure_resource_group": None,
    }


def test_azure_requires_subscription_and_resource_group(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        _parse(["--cloud-type", "azure", *COMMON_ARGS], monkeypatch)


def test_release_notes_url_is_derived_from_version() -> None:
    assert CloudPublisher.build_release_notes_url("2.2.0p5") == (
        "https://forum.checkmk.com/t/release-checkmk-stable-release-2-2-0p5/"
    )


@pytest.mark.parametrize(
    "version",
    [pytest.param("2.4.0p5", id="patch release"), pytest.param("2.4.0", id="base release")],
)
def test_official_releases_are_accepted(version: str) -> None:
    assert ensure_using_official_release(version) == Version.from_str(version)


@pytest.mark.parametrize(
    "version",
    [pytest.param("2.4.0-2026.01.01", id="daily"), pytest.param("2.4.0b3", id="beta")],
)
def test_unofficial_releases_are_rejected(version: str) -> None:
    with pytest.raises(RuntimeError, match="only want to publish official patch releases"):
        ensure_using_official_release(version)


class _FakeMarketplace:
    def __init__(self, statuses: Sequence[str]) -> None:
        self.statuses = list(statuses)
        self.change_sets: list[dict[str, object]] = []

    def start_change_set(self, **kwargs: object) -> dict[str, str]:
        self.change_sets.append(kwargs)
        return {"ChangeSetId": "cs-1"}

    def describe_change_set(self, **_kwargs: object) -> dict[str, object]:
        return {
            "Status": self.statuses.pop(0),
            "ChangeSet": [{"ErrorDetailList": ["scanner refused"]}],
        }


class _FakeEC2:
    def __init__(self, image_ids: Sequence[str]) -> None:
        self.image_ids = image_ids

    def describe_images(self, **_kwargs: object) -> dict[str, list[dict[str, str]]]:
        return {"Images": [{"ImageId": image_id} for image_id in self.image_ids]}


@pytest.fixture(name="aws_publisher")
def fixture_aws_publisher(monkeypatch: pytest.MonkeyPatch) -> AWSPublisher:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    monkeypatch.setattr(AWSPublisher, "SECONDS_TO_WAIT_FOR_NEXT_STATUS", 0)
    return AWSPublisher(VERSION, "job-1", "cmk-image", "arn:scanner", "prod-1")


def test_aws_publish_submits_change_set_and_waits_for_success(
    aws_publisher: AWSPublisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    marketplace = _FakeMarketplace(["PREPARING", "APPLYING", "UNKNOWN", "SUCCEEDED"])
    monkeypatch.setattr(aws_publisher, "client_ec2", _FakeEC2(["ami-123"]))
    monkeypatch.setattr(aws_publisher, "client_market", marketplace)

    asyncio.run(aws_publisher.publish())

    (change_set,) = marketplace.change_sets
    assert change_set["ChangeSetName"] == "Add new version 2.4.0p5 by job-1"
    change = change_set["ChangeSet"][0]  # type: ignore[index]
    assert change["Entity"] == {"Type": "AmiProduct@1.0", "Identifier": "prod-1"}
    details = json.loads(change["Details"])
    assert details["Version"]["VersionTitle"] == "2.4.0p5"
    ami_source = details["DeliveryOptions"][0]["Details"]["AmiDeliveryOptionDetails"]["AmiSource"]
    assert ami_source["AmiId"] == "ami-123"
    assert ami_source["AccessRoleArn"] == "arn:scanner"


def test_aws_publish_fails_when_change_set_fails(
    aws_publisher: AWSPublisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(aws_publisher, "client_ec2", _FakeEC2(["ami-123"]))
    monkeypatch.setattr(aws_publisher, "client_market", _FakeMarketplace(["FAILED"]))

    with pytest.raises(RuntimeError, match="scanner refused"):
        asyncio.run(aws_publisher.publish())


def test_aws_publish_requires_exactly_one_matching_image(
    aws_publisher: AWSPublisher, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(aws_publisher, "client_ec2", _FakeEC2(["ami-1", "ami-2"]))

    with pytest.raises(AssertionError, match="Cannot identify the correct image"):
        aws_publisher.get_ami_image_id()


class _FakePoller:
    def __init__(self, provisioning_state: str) -> None:
        self._provisioning_state = provisioning_state

    def result(self, _timeout: int) -> GalleryImageVersion:
        version = GalleryImageVersion(location="westeurope")
        version.provisioning_state = self._provisioning_state
        return version


class _FakeGalleryImageVersions:
    def __init__(self, provisioning_state: str) -> None:
        self.created: list[dict[str, object]] = []
        self._provisioning_state = provisioning_state

    def begin_create_or_update(self, **kwargs: object) -> _FakePoller:
        self.created.append(kwargs)
        return _FakePoller(self._provisioning_state)


def _azure_publisher(
    monkeypatch: pytest.MonkeyPatch, image_ids: Sequence[str | None], provisioning_state: str
) -> tuple[AzurePublisher, _FakeGalleryImageVersions]:
    publisher = AzurePublisher(VERSION, "job-1", "cmk-image", "sub-1", "rg-1")
    gallery = _FakeGalleryImageVersions(provisioning_state)
    monkeypatch.setattr(
        publisher,
        "resource_client",
        SimpleNamespace(
            resources=SimpleNamespace(
                list_by_resource_group=lambda _rg, **_kwargs: iter(
                    SimpleNamespace(id=image_id) for image_id in image_ids
                )
            )
        ),
    )
    monkeypatch.setattr(
        publisher, "compute_client", SimpleNamespace(gallery_image_versions=gallery)
    )
    return publisher, gallery


def test_azure_version_drops_the_patch_marker() -> None:
    assert AzurePublisher.azure_compatible_version(Version.from_str("2.2.0p5")) == "2.2.5"


def test_azure_publish_creates_gallery_image_from_unique_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publisher, gallery = _azure_publisher(monkeypatch, ["/images/cmk-image"], "Succeeded")

    asyncio.run(publisher.publish())

    (created,) = gallery.created
    assert created["gallery_image_version_name"] == "2.4.5"
    assert created["resource_group_name"] == "rg-1"
    gallery_version = created["gallery_image_version"]
    assert isinstance(gallery_version, GalleryImageVersion)
    assert gallery_version.properties is not None
    assert gallery_version.properties.storage_profile.source is not None
    assert gallery_version.properties.storage_profile.source.id == "/images/cmk-image"


def test_azure_publish_fails_on_unsuccessful_provisioning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publisher, _gallery = _azure_publisher(monkeypatch, ["/images/cmk-image"], "Failed")

    with pytest.raises(RuntimeError, match="Poller returned provisioning_state="):
        asyncio.run(publisher.publish())


def test_azure_image_lookup_rejects_ambiguous_names(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, _gallery = _azure_publisher(monkeypatch, ["/images/a", "/images/b"], "Succeeded")

    with pytest.raises(RuntimeError, match="Found also"):
        publisher.get_azure_image_id()


def test_azure_image_lookup_rejects_image_without_id(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, _gallery = _azure_publisher(monkeypatch, [None], "Succeeded")

    with pytest.raises(RuntimeError, match="Got no results"):
        publisher.get_azure_image_id()
