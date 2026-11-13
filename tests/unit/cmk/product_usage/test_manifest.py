#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import uuid
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import jsonschema
import pytest

from cmk.product_usage.manifest import build_cloud_trial_manifest, build_manifest, main
from cmk.product_usage.schema import (
    CloudTrialPayload,
    GrafanaUsageData,
    InventoryData,
    ProductUsagePayload,
)

type BuildManifest = Callable[[], dict[str, object]]

PAYLOAD_MANIFESTS = [
    pytest.param(ProductUsagePayload, build_manifest, id="product usage"),
    pytest.param(CloudTrialPayload, build_cloud_trial_manifest, id="cloud trial"),
]


def _payload(
    payload_type: type[ProductUsagePayload], grafana: GrafanaUsageData | None
) -> ProductUsagePayload:
    return payload_type(
        id=uuid.UUID("0f8fad5b-d9cb-469f-a165-70867728950e"),
        count_hosts=1,
        count_services=2,
        count_folders=3,
        edition="community",
        cmk_version="2.5.0p1",
        os="Ubuntu 24.04.3 LTS",
        users={
            "humans": {
                "total": 1,
                "by_role": {"admin": 1},
                "by_connector_type": {"htpasswd": 1},
                "active": {"24h": 1, "7d": 1, "30d": 1},
            },
            "automation": {
                "total": 0,
                "by_role": {},
                "by_connector_type": {},
                "active": {"24h": 0, "7d": 0, "30d": 0},
            },
        },
        timestamp=1767700800,
        checks={"check_mk-df": {"count": 1, "count_hosts": 1, "count_disabled": 0}},
        inventory=InventoryData(hosts_with_inventory=4),
        grafana=grafana,
    )


def _undocumented_fields(schema: Mapping[str, object], path: str) -> Iterator[str]:
    properties = schema.get("properties", {})
    assert isinstance(properties, Mapping)
    for name, field in properties.items():
        if "description" not in field or "examples" not in field:
            yield f"{path}.{name}"


@pytest.mark.parametrize(
    ("flags", "manifest"),
    [
        pytest.param([], build_manifest, id="product usage"),
        pytest.param(["--cloud-trial"], build_cloud_trial_manifest, id="cloud trial"),
    ],
)
def test_manifest_cli_writes_a_valid_json_schema(
    tmp_path: Path, flags: list[str], manifest: BuildManifest
) -> None:
    manifest_path = tmp_path / "manifest.json"

    exit_code = main([*flags, str(manifest_path)])

    assert exit_code == 0
    written = json.loads(manifest_path.read_text())
    jsonschema.Draft202012Validator.check_schema(written)
    assert written == manifest()


@pytest.mark.parametrize(("payload_type", "manifest"), PAYLOAD_MANIFESTS)
@pytest.mark.parametrize(
    "grafana",
    [
        pytest.param(None, id="without grafana"),
        pytest.param(
            GrafanaUsageData(is_used=True, version="12.3.0", is_grafana_cloud=True),
            id="with grafana",
        ),
    ],
)
def test_transmitted_payload_conforms_to_manifest(
    payload_type: type[ProductUsagePayload],
    manifest: BuildManifest,
    grafana: GrafanaUsageData | None,
) -> None:
    document = json.loads(_payload(payload_type, grafana).model_dump_with_metadata_json())

    jsonschema.validate(document, manifest())


def test_payload_with_foreign_metadata_violates_manifest() -> None:
    document = json.loads(_payload(ProductUsagePayload, None).model_dump_with_metadata_json())
    document["metadata"]["version"] = "v0"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, build_manifest())


@pytest.mark.parametrize(
    "manifest",
    [
        pytest.param(build_manifest, id="product usage"),
        pytest.param(build_cloud_trial_manifest, id="cloud trial"),
    ],
)
def test_every_field_has_description_and_example(manifest: BuildManifest) -> None:
    built = manifest()
    properties = built["properties"]
    assert isinstance(properties, Mapping)
    definitions = built["$defs"]
    assert isinstance(definitions, Mapping)

    undocumented = [
        *_undocumented_fields(properties["data"], "data"),
        *(
            field
            for name, definition in definitions.items()
            for field in _undocumented_fields(definition, name)
        ),
    ]

    assert undocumented == []


@pytest.mark.parametrize(("payload_type", "manifest"), PAYLOAD_MANIFESTS)
def test_field_examples_form_a_payload_conforming_to_manifest(
    payload_type: type[ProductUsagePayload], manifest: BuildManifest
) -> None:
    built = manifest()
    properties = built["properties"]
    assert isinstance(properties, Mapping)
    data_properties = properties["data"]["properties"]

    document = {
        "metadata": payload_type.metadata,
        "data": {name: field["examples"][0] for name, field in data_properties.items()},
    }

    jsonschema.validate(document, built)
