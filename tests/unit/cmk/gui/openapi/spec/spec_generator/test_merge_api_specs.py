#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import cast

import pytest
import yaml
from openapi_spec_validator import validate

from cmk.gui.openapi.spec.spec_generator.merge_api_specs import merge_specs, MergeConflictError


def _spec(
    paths: dict[str, object] | None = None,
    schemas: dict[str, object] | None = None,
    tags: list[dict[str, object]] | None = None,
    tag_groups: list[dict[str, object]] | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "openapi": "3.1.1",
        "info": {"title": "Checkmk REST-API", "version": "internal"},
        "paths": paths or {},
        "components": {"schemas": schemas or {}},
        "tags": tags or [],
        "x-tagGroups": tag_groups or [],
        **(extra or {}),
    }


def _operation(operation_id: str) -> dict[str, object]:
    return {"operationId": operation_id, "responses": {"200": {"description": "OK"}}}


def test_disjoint_paths_are_unioned() -> None:
    merged = merge_specs(
        {
            "community": _spec(paths={"/common": {"get": _operation("common")}}),
            "ultimate": _spec(
                paths={
                    "/common": {"get": _operation("common"), "post": _operation("common_post")},
                    "/ultimate-only": {"get": _operation("ultimate_only")},
                }
            ),
        }
    )

    assert merged["paths"] == {
        "/common": {"get": _operation("common"), "post": _operation("common_post")},
        "/ultimate-only": {"get": _operation("ultimate_only")},
    }


def test_identical_schemas_are_deduplicated() -> None:
    schemas: dict[str, object] = {"Host": {"type": "object"}}
    merged = merge_specs({"community": _spec(schemas=schemas), "pro": _spec(schemas=schemas)})

    assert merged["components"] == {"schemas": schemas}


def test_divergent_operation_raises_with_editions_and_location() -> None:
    with pytest.raises(MergeConflictError, match=r"paths//host/get .*pro and ultimate"):
        merge_specs(
            {
                "pro": _spec(paths={"/host": {"get": _operation("pro_variant")}}),
                "ultimate": _spec(paths={"/host": {"get": _operation("ultimate_variant")}}),
            }
        )


def test_divergent_schema_raises() -> None:
    with pytest.raises(MergeConflictError, match="components/schemas/Host"):
        merge_specs(
            {
                "pro": _spec(schemas={"Host": {"type": "object"}}),
                "ultimate": _spec(schemas={"Host": {"type": "string"}}),
            }
        )


@pytest.mark.parametrize(
    "editions",
    [
        ("community", "ultimatemt"),
        ("ultimatemt", "community"),
    ],
)
def test_description_only_divergence_prefers_higher_ranked_edition(
    editions: tuple[str, str],
) -> None:
    # The same endpoint documents edition-specific permissions differently (a permission
    # declared via OkayToIgnorePerm only renders where its component is present). The
    # higher-ranked edition's copy wins regardless of input order.
    base = _operation("list_dashboards")
    lean = base | {"description": "requires: general.edit_dashboards"}
    rich = base | {"description": "requires: general.edit_dashboards, general.edit_custom_graph"}
    specs = {"community": _spec(paths={"/dash": {"get": lean}})}
    specs["ultimatemt"] = _spec(paths={"/dash": {"get": rich}})

    merged = merge_specs({edition: specs[edition] for edition in editions})

    assert merged["paths"] == {"/dash": {"get": rich}}


def test_divergence_beyond_description_still_raises() -> None:
    # A difference outside the description is a real conflict, even when the description
    # also differs.
    with pytest.raises(MergeConflictError, match="paths//dash/get"):
        merge_specs(
            {
                "community": _spec(
                    paths={"/dash": {"get": _operation("read") | {"description": "a"}}}
                ),
                "ultimate": _spec(
                    paths={"/dash": {"get": _operation("list") | {"description": "b"}}}
                ),
            }
        )


def test_divergent_metadata_raises() -> None:
    with pytest.raises(MergeConflictError, match="info"):
        merge_specs(
            {
                "community": _spec(),
                "pro": _spec() | {"info": {"title": "Other", "version": "internal"}},
            }
        )


def test_metadata_key_missing_in_one_edition_raises() -> None:
    with pytest.raises(MergeConflictError, match="x-logo"):
        merge_specs({"community": _spec(), "pro": _spec(extra={"x-logo": {"url": "logo.png"}})})


def test_tags_and_tag_groups_are_unioned() -> None:
    merged = merge_specs(
        {
            "community": _spec(
                tags=[{"name": "Host"}],
                tag_groups=[{"name": "Setup", "tags": ["Host"]}],
            ),
            "ultimate": _spec(
                tags=[{"name": "Host"}, {"name": "Relay"}],
                tag_groups=[{"name": "Setup", "tags": ["Host", "Relay"]}],
            ),
        }
    )

    assert merged["tags"] == [{"name": "Host"}, {"name": "Relay"}]
    assert merged["x-tagGroups"] == [{"name": "Setup", "tags": ["Host", "Relay"]}]


def test_divergent_tag_raises() -> None:
    with pytest.raises(MergeConflictError, match="tags/Host"):
        merge_specs(
            {
                "community": _spec(tags=[{"name": "Host", "x-displayName": "Hosts"}]),
                "pro": _spec(tags=[{"name": "Host", "x-displayName": "Hosts!"}]),
            }
        )


def test_unknown_edition_raises() -> None:
    with pytest.raises(ValueError, match="managed"):
        merge_specs({"managed": _spec()})


def test_output_is_independent_of_input_order() -> None:
    specs = {
        "community": _spec(paths={"/a": {"get": _operation("a")}}),
        "ultimate": _spec(paths={"/b": {"get": _operation("b")}}),
    }
    shuffled = {edition: specs[edition] for edition in reversed(list(specs))}

    assert yaml.safe_dump(merge_specs(specs), sort_keys=False) == yaml.safe_dump(
        merge_specs(shuffled), sort_keys=False
    )


def test_single_input_passes_through_normalized() -> None:
    spec = _spec(paths={"/b": {"get": _operation("b")}, "/a": {"get": _operation("a")}})
    merged = merge_specs({"community": spec})

    assert list(cast(dict[str, object], merged["paths"])) == ["/a", "/b"]
    assert merged["paths"] == spec["paths"]


def test_merged_spec_is_valid_openapi() -> None:
    merged = merge_specs(
        {
            "community": _spec(paths={"/common": {"get": _operation("common")}}),
            "ultimate": _spec(paths={"/ultimate-only": {"get": _operation("ultimate_only")}}),
        }
    )

    validate(cast(Mapping[str, object], merged))
