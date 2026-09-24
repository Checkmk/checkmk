#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import uuid
from collections.abc import Iterator, Mapping
from pathlib import Path

import jsonschema
import pytest

from cmk.product_usage.manifest import build_manifest, main
from cmk.product_usage.schema import GrafanaUsageData, ProductUsagePayload


def _payload(grafana: GrafanaUsageData | None) -> ProductUsagePayload:
    return ProductUsagePayload(
        id=uuid.UUID("0f8fad5b-d9cb-469f-a165-70867728950e"),
        count_hosts=1,
        count_services=2,
        count_folders=3,
        edition="community",
        cmk_version="2.5.0p1",
        timestamp=1767700800,
        checks={"check_mk-df": {"count": 1, "count_hosts": 1, "count_disabled": 0}},
        grafana=grafana,
    )


def _undocumented_fields(schema: Mapping[str, object], path: str) -> Iterator[str]:
    properties = schema.get("properties", {})
    assert isinstance(properties, Mapping)
    for name, field in properties.items():
        if "description" not in field or "examples" not in field:
            yield f"{path}.{name}"


def test_manifest_cli_writes_a_valid_json_schema(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"

    exit_code = main([str(manifest_path)])

    assert exit_code == 0
    jsonschema.Draft202012Validator.check_schema(json.loads(manifest_path.read_text()))


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
def test_transmitted_payload_conforms_to_manifest(grafana: GrafanaUsageData | None) -> None:
    document = json.loads(_payload(grafana).model_dump_with_metadata_json())

    jsonschema.validate(document, build_manifest())


def test_payload_with_foreign_metadata_violates_manifest() -> None:
    document = json.loads(_payload(None).model_dump_with_metadata_json())
    document["metadata"]["version"] = "v0"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, build_manifest())


def test_every_field_has_description_and_example() -> None:
    manifest = build_manifest()
    properties = manifest["properties"]
    assert isinstance(properties, Mapping)
    definitions = manifest["$defs"]
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


def test_field_examples_form_a_payload_conforming_to_manifest() -> None:
    manifest = build_manifest()
    properties = manifest["properties"]
    assert isinstance(properties, Mapping)
    data_properties = properties["data"]["properties"]

    document = {
        "metadata": ProductUsagePayload.metadata,
        "data": {name: field["examples"][0] for name, field in data_properties.items()},
    }

    jsonschema.validate(document, manifest)
