#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import argparse
import asyncio
import enum
import json
import os
import sys
from typing import Final

import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    GalleryArtifactVersionSource,
    GalleryImageVersion,
    GalleryImageVersionPublishingProfile,
    GalleryImageVersionStorageProfile,
    GalleryOSDiskImage,
    TargetRegion,
)
from azure.mgmt.resource import ResourceManagementClient
from msrest.polling import LROPoller

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from cmk.ccc.version import _BaseVersion, ReleaseType, Version


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="This script is used for publishing new versions "
        "for our AWS and Azure cloud images."
    )
    parser.add_argument(
        "--cloud-type",
        help="Choose here the type of the cloud",
        action="store",
        required=True,
        choices=CloudPublisher.CLOUD_TYPES,
    )
    parser.add_argument(
        "--new-version",
        help="The new version which will be used for the update",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--build-tag",
        help="The jenkins build tag to pass to the change sets for later identification",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--image-name",
        help="The name of the cloud image which can be found in the cloud",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--marketplace-scanner-arn",
        help="The arn of an aws role which can access our ami images",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--product-id",
        help="The product id of the product which should receive a new version",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--azure-subscription-id",
        help="Azure's subscription id",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--azure-resource-group",
        help="Azure's resource group",
        action="store",
        required=True,
    )
    return parser.parse_args()


class CloudPublisher(abc.ABC):
    # Currently, both AWS and Azure should long be finished after that time
    SECONDS_TO_TIMEOUT_PUBLISH_PROCESS: Final = 3 * 60 * 60
    CLOUD_TYPES: Final = ["aws", "azure"]
    SECONDS_TO_WAIT_FOR_NEXT_STATUS: Final = 20

    def __init__(self, version: Version, build_tag: str, image_name: str):
        self.version = version
        self.build_tag = build_tag
        self.image_name = image_name

    @abc.abstractmethod
    async def publish(self): ...

    @staticmethod
    def build_release_notes_url(version: str) -> str:
        """
        >>> CloudPublisher.build_release_notes_url("2.2.0p5")
        'https://forum.checkmk.com/t/release-checkmk-stable-release-2-2-0p5/'
        """
        return (
            f"https://forum.checkmk.com/t/release-checkmk-stable-release-"
            f"{version.replace('.', '-')}/"
        )


class AWSPublisher(CloudPublisher):
    ENTITY_TYPE_WITH_VERSION = "AmiProduct@1.0"
    CATALOG = "AWSMarketplace"

    def __init__(
        self,
        version: Version,
        build_tag: str,
        image_name: str,
        marketplace_scanner_arn: str,
        product_id: str,
    ):
        super().__init__(version, build_tag, image_name)
        self.client_ec2 = boto3.client("ec2")
        self.client_market = boto3.client("marketplace-catalog")
        self.aws_marketplace_scanner_arn = marketplace_scanner_arn
        self.production_id = product_id

    class ChangeTypes(enum.StrEnum):
        ADD_DELIVERY_OPTIONS = "AddDeliveryOptions"  # for updating the version

    async def publish(self) -> None:
        image_id = self.get_ami_image_id()
        update_details = {
            "Version": {
                "VersionTitle": str(self.version),
                "ReleaseNotes": self.build_release_notes_url(str(self.version)),
            },
            "DeliveryOptions": [
                {
                    "Details": {
                        "AmiDeliveryOptionDetails": {
                            "AmiSource": {
                                "AmiId": image_id,
                                # This role must be able to read our ami images, see:
                                # https://docs.aws.amazon.com/marketplace/latest/userguide/ami-single-ami-products.html#single-ami-marketplace-ami-access
                                "AccessRoleArn": self.aws_marketplace_scanner_arn,
                                "UserName": "ubuntu",
                                "OperatingSystemName": "UBUNTU",
                                # TODO: can we centralize this into editions.yml?
                                "OperatingSystemVersion": "22.04",
                            },
                            "UsageInstructions": "See the Checkmk manual for "
                            "detailed usage instructions: "
                            "https://docs.checkmk.com/latest/en/intro_gui.html",
                            "RecommendedInstanceType": "c6a.large",
                            "SecurityGroups": [
                                {
                                    # ssh
                                    "IpProtocol": "tcp",
                                    "FromPort": 22,
                                    "ToPort": 22,
                                    "IpRanges": ["0.0.0.0/0"],
                                },
                                {
                                    # https
                                    "IpProtocol": "tcp",
                                    "FromPort": 443,
                                    "ToPort": 443,
                                    "IpRanges": ["0.0.0.0/0"],
                                },
                                {
                                    # agent registration
                                    "IpProtocol": "tcp",
                                    "FromPort": 8000,
                                    "ToPort": 8000,
                                    "IpRanges": ["0.0.0.0/0"],
                                },
                            ],
                        }
                    }
                }
            ],
        }

        print(f"Starting change set for ami image {image_id} and version {self.version}")
        response = self.client_market.start_change_set(
            Catalog=self.CATALOG,
            ChangeSet=[
                {
                    "ChangeType": self.ChangeTypes.ADD_DELIVERY_OPTIONS,
                    "Entity": {
                        "Type": self.ENTITY_TYPE_WITH_VERSION,
                        "Identifier": self.production_id,
                    },
                    "Details": json.dumps(update_details),
                    "ChangeName": "update",
                },
            ],
            ChangeSetName=f"Add new version {self.version} by {self.build_tag}",
        )
        await asyncio.wait_for(
            self.update_successful(response["ChangeSetId"]), self.SECONDS_TO_TIMEOUT_PUBLISH_PROCESS
        )

    def get_ami_image_id(self) -> str:
        images = self.client_ec2.describe_images(
            Filters=[
                {
                    "Name": "name",
                    "Values": [self.image_name],
                },
            ],
        )["Images"]
        assert len(images) == 1, (
            f"Cannot identify the correct image to publish, received the following: {images}"
        )
        return images[0]["ImageId"]

    async def update_successful(self, change_set_id: str) -> None:
        while True:
            response = self.client_market.describe_change_set(
                Catalog=self.CATALOG,
                ChangeSetId=change_set_id,
            )
            status = response["Status"]
            match status:
                case "PREPARING" | "APPLYING":
                    print(
                        f"Got {status=}... "
                        f"sleeping for {self.SECONDS_TO_WAIT_FOR_NEXT_STATUS} seconds..."
                    )
                    await asyncio.sleep(self.SECONDS_TO_WAIT_FOR_NEXT_STATUS)
                case "CANCELLED" | "FAILED":
                    raise RuntimeError(
                        f"The changeset {change_set_id} returned {status=}.\n"
                        f"The error was: {response['ChangeSet'][0]['ErrorDetailList']}"
                    )
                case "SUCCEEDED":
                    return


class AzurePublisher(CloudPublisher):
    LOCATION = "westeurope"
    STORAGE_ACCOUNT_TYPE = "Standard_LRS"
    GALLERY_NAME = "Marketplace_Publishing_Gallery"

    def __init__(
        self,
        version: Version,
        build_tag: str,
        image_name: str,
        subscription_id: str,
        resource_group: str,
    ):
        super().__init__(version, build_tag, image_name)
        assert self.version is not None

        credentials = DefaultAzureCredential()
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        # The image name is hardcoded, because we changing this for each new
        # major or minor version would require going through the complete
        # listing process again.
        # The gallery ID is only visible internally and not visible by users.
        # Use Checkmk_Cloud_Edition_2.2b5 for e.g. testing
        self.gallery_image_name = "Checkmk-Cloud-Edition-2.2"
        self.compute_client = ComputeManagementClient(
            credentials,
            self.subscription_id,
        )
        self.resource_client = ResourceManagementClient(
            credentials,
            self.subscription_id,
        )

    def get_azure_image_id(self) -> str:
        resource_list = self.resource_client.resources.list_by_resource_group(
            self.resource_group,
            filter=f"name eq '{self.image_name}'",
        )
        first_id = next(resource_list).id
        if another_match := next(resource_list, None):
            raise RuntimeError(
                f"Cannot identify a unique azure image by using {self.image_name=}. "
                f"Found also: {another_match}"
            )

        return first_id

    @staticmethod
    def azure_compatible_version(version: Version) -> str:
        """
        Yea, this is great... but azure doesn't accept our versioning schema
        >>> AzurePublisher.azure_compatible_version(Version.from_str("2.2.0p5"))
        '2.2.5'
        """
        assert isinstance(version.base, _BaseVersion)
        return f"{version.base.major}.{version.base.minor}.{version.release.value}"

    async def build_gallery_image(self):
        image_id = self.get_azure_image_id()
        print(f"Creating new gallery image from {self.version=} by using {image_id=}")
        self.update_succesful(
            self.compute_client.gallery_image_versions.begin_create_or_update(
                resource_group_name=self.resource_group,
                gallery_name=self.GALLERY_NAME,
                gallery_image_name=self.gallery_image_name,
                gallery_image_version_name=self.azure_compatible_version(self.version),
                gallery_image_version=GalleryImageVersion(
                    location=self.LOCATION,
                    publishing_profile=GalleryImageVersionPublishingProfile(
                        target_regions=[
                            TargetRegion(name=self.LOCATION),
                        ],
                        storage_account_type=self.STORAGE_ACCOUNT_TYPE,
                    ),
                    storage_profile=GalleryImageVersionStorageProfile(
                        source=GalleryArtifactVersionSource(
                            id=image_id,
                        ),
                        os_disk_image=GalleryOSDiskImage(
                            # Taken from previous images
                            host_caching="ReadWrite",
                        ),
                    ),
                ),
            ),
        )

    async def publish(self):
        """
        Azure's update process has 2 steps:
        * first, we need to create a gallery image from the VM image which was pushed by packer
        * second, we need to add the new gallery image as technical configuration to our marketplace
        offer
        """

        await asyncio.wait_for(
            self.build_gallery_image(),
            self.SECONDS_TO_TIMEOUT_PUBLISH_PROCESS,
        )

        # TODO: Implement step #2

    def update_succesful(self, poller: LROPoller) -> None:
        while True:
            result = poller.result(self.SECONDS_TO_WAIT_FOR_NEXT_STATUS)
            assert isinstance(result, GalleryImageVersion)
            if provisioning_state := result.provisioning_state:
                print(f"{provisioning_state=}")
                match provisioning_state:
                    case "Succeeded":
                        return
                    case _:
                        raise RuntimeError(f"Poller returned {provisioning_state=}")
            print(
                f"Got no result yet... "
                f"sleeping for {self.SECONDS_TO_WAIT_FOR_NEXT_STATUS} seconds..."
            )


def ensure_using_official_release(version: str) -> Version:
    parsed_version = Version.from_str(version)
    if parsed_version.release.release_type not in (ReleaseType.p, ReleaseType.na):
        raise RuntimeError(
            f"We only want to publish official patch releases, got {parsed_version} instead."
        )
    return parsed_version


if __name__ == "__main__":
    args = parse_arguments()

    new_version = ensure_using_official_release(args.new_version)
    match args.cloud_type:
        case "aws":
            asyncio.run(
                AWSPublisher(
                    new_version,
                    args.build_tag,
                    args.image_name,
                    args.marketplace_scanner_arn,
                    args.product_id,
                ).publish()
            )
        case "azure":
            asyncio.run(
                AzurePublisher(
                    new_version,
                    args.build_tag,
                    args.image_name,
                    args.azure_subscription_id,
                    args.azure_resource_group,
                ).publish()
            )
