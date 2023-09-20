#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import argparse
import asyncio
import enum
import json
from typing import Final

import boto3  # type: ignore[import]


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
    return parser.parse_args()


class CloudPublisher(abc.ABC):
    # Currently, both AWS and Azure should long be finished after that time
    SECONDS_TO_TIMEOUT_PUBLISH_PROCESS: Final = 3 * 60 * 60
    CLOUD_TYPES: Final = ["aws", "azure"]
    SECONDS_TO_WAIT_FOR_NEXT_STATUS: Final = 20

    def __init__(self, version: str, build_tag: str, image_name: str):
        self.version = version
        self.build_tag = build_tag
        self.image_name = image_name

    @abc.abstractmethod
    async def publish(self):
        ...

    @staticmethod
    def build_release_notes_url(version: str) -> str:
        """
        >>> CloudPublisher.build_release_notes_url("2.2.0p5")
        'https://forum.checkmk.com/t/release-checkmk-stable-release-2-2-0p5/'
        """
        return (
            f"https://forum.checkmk.com/t/release-checkmk-stable-release-"
            f"{version.replace('.','-')}/"
        )


class AWSPublisher(CloudPublisher):
    ENTITY_TYPE_WITH_VERSION = "AmiProduct@1.0"
    CATALOG = "AWSMarketplace"

    def __init__(
        self,
        version: str,
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
                "VersionTitle": self.version,
                "ReleaseNotes": self.build_release_notes_url(self.version),
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
            "Cannot identify the correct image to publish, " f"received the following: {images}"
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


if __name__ == "__main__":
    args = parse_arguments()
    match args.cloud_type:
        case "aws":
            asyncio.run(
                AWSPublisher(
                    args.new_version,
                    args.build_tag,
                    args.image_name,
                    args.marketplace_scanner_arn,
                    args.product_id,
                ).publish()
            )
        case "azure":
            print("TO BE IMPLEMENTED")
