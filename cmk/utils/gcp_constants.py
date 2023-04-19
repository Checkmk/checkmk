#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing

RegionMap: typing.Final = {
    # Download from:
    # https://github.com/GoogleCloudPlatform/gcping/blob/main/tools/terraform/regions.json
    # Changes to the right-hand side of this list cause an incompatible change to the service name
    # of the check `gcp_status`
    "asia-east1": "Taiwan",
    "asia-east2": "Hong Kong",
    "asia-northeast1": "Tokyo",
    "asia-northeast2": "Osaka",
    "asia-northeast3": "Seoul",
    "asia-south1": "Mumbai",
    "asia-south2": "Delhi",
    "asia-southeast1": "Singapore",
    "asia-southeast2": "Jakarta",
    "australia-southeast1": "Sydney",
    "australia-southeast2": "Melbourne",
    "europe-central2": "Warsaw",
    "europe-north1": "Finland",
    "europe-west1": "Belgium",
    "europe-west2": "London",
    "europe-west3": "Frankfurt",
    "europe-west4": "Netherlands",
    "europe-west6": "Zurich",
    "europe-west8": "Milan",
    "europe-west9": "Paris",
    "europe-southwest1": "Madrid",
    "me-west1": "Tel Aviv",
    "northamerica-northeast1": "Montréal",
    "northamerica-northeast2": "Toronto",
    "southamerica-east1": "São Paulo",
    "southamerica-west1": "Santiago",
    "us-central1": "Iowa",
    "us-east1": "South Carolina",
    "us-east4": "North Virginia",
    "us-east5": "Columbus",
    "us-south1": "Dallas",
    "us-west1": "Oregon",
    "us-west2": "Los Angeles",
    "us-west3": "Salt Lake City",
    "us-west4": "Las Vegas",
}
