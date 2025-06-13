#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing

from cmk.plugins.gcp.lib.gcp import AssetType, GCPAsset, Item

RegionMap: typing.Final = {
    # ATTENTION!
    # Changes to the right-hand side of this list cause an incompatible change to the service name
    # of the check `gcp_status`
    #
    # This is no longer a general purpose GCP-RegionMap, but tied to the incident.json
    # as there are "Multi-Region" regions as us or europe.
    #
    # Source 1:
    # https://github.com/GoogleCloudPlatform/gcping/blob/main/tools/terraform/regions.json
    "africa-south1": "Johannesburg",
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
    "europe-north2": "Stockholm",
    "europe-west1": "Belgium",
    "europe-west2": "London",
    "europe-west3": "Frankfurt",
    "europe-west4": "Netherlands",
    "europe-west6": "Zurich",
    "europe-west8": "Milan",
    "europe-west9": "Paris",
    "europe-west10": "Berlin",
    "europe-west12": "Turin",
    "europe-southwest1": "Madrid",
    "me-central1": "Doha",
    "me-central2": "Dammam",
    "me-west1": "Tel Aviv",
    "northamerica-northeast1": "Montréal",
    "northamerica-northeast2": "Toronto",
    "northamerica-south1": "Mexico",
    "southamerica-east1": "São Paulo",
    "southamerica-west1": "Santiago",
    "us-central1": "Iowa",
    "us-east1": "South Carolina",
    "us-east4": "Northern Virginia",
    "us-east5": "Columbus",
    "us-south1": "Dallas",
    "us-west1": "Oregon",
    "us-west2": "Los Angeles",
    "us-west3": "Salt Lake City",
    "us-west4": "Las Vegas",
    # Source 2:
    # curl https://status.cloud.google.com/incidents.json | \
    #      jq '[.[].previously_affected_locations[] | "\(.id) -- \(.title)"] | unique | sort'
    "asia": "Multi-Region Asia",
    "asia1": "Multi-Region Asia 1",
    "eu": "Multi-Region EU",
    "eur3": "Multi-Region EUR3",
    "eur4": "Multi-Region EUR4",
    "eur5": "Multi-Region EUR5",
    "europe": "Multi-Region Europe",
    "nam-eur-asia1": "Multi-Region NAM-EUR-ASIA1",
    "nam10": "Multi-Region NAM10",
    "nam11": "Multi-Region NAM11",
    "nam12": "Multi-Region NAM12",
    "nam13": "Multi-Region NAM13",
    "nam3": "Multi-Region NAM3",
    "nam5": "Multi-Region NAM5",
    "nam6": "Multi-Region NAM6",
    "nam7": "Multi-Region NAM7",
    "nam8": "Multi-Region NAM8",
    "nam9": "Multi-Region NAM9",
    "us": "Multi-Region US",
    # Global is special: it can not be ignored. so its not part of this list.
}

# Known asset types that downstream checks can work with. Ignore others
Extractors: typing.Mapping[AssetType, typing.Callable[[GCPAsset], Item]] = {
    AssetType("file.googleapis.com/Instance"): lambda a: a.resource_data["name"].split("/")[-1],
    AssetType("cloudfunctions.googleapis.com/CloudFunction"): lambda a: a.resource_data[
        "name"
    ].split("/")[-1],
    AssetType("storage.googleapis.com/Bucket"): lambda a: a.resource_data["id"],
    AssetType("redis.googleapis.com/Instance"): lambda a: a.resource_data["name"],
    AssetType("run.googleapis.com/Service"): lambda a: a.resource_data["metadata"]["name"],
    AssetType("sqladmin.googleapis.com/Instance"): lambda a: a.resource_data["name"],
    AssetType("compute.googleapis.com/Instance"): lambda a: a.resource_data["name"],
    AssetType("compute.googleapis.com/Disk"): lambda a: a.resource_data["name"],
    AssetType("compute.googleapis.com/UrlMap"): lambda a: a.resource_data["name"],
}
