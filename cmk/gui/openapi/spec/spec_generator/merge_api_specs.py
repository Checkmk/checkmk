#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import difflib
import json
import sys
from collections.abc import Mapping, Sequence, Set
from pathlib import Path
from typing import override

import yaml

from cmk.ccc.version import Edition

# TODO: editions should introduce their own endpoints instead of redefining shared ones with
#  different models. Each entry names the diverging edition, whose copy is dropped from the merge.
_KNOWN_DIVERGENT_PATHS = frozenset(
    {
        ("cloud", "post", "/domain-types/otel_collector_config_bundles/collections/all"),
        ("cloud", "get", "/domain-types/otel_collector_config_receivers/collections/all"),
        ("cloud", "post", "/domain-types/otel_collector_config_receivers/collections/all"),
        ("cloud", "delete", "/objects/otel_collector_config_receivers/{config_id}"),
        ("cloud", "get", "/objects/otel_collector_config_receivers/{config_id}"),
    }
)
_KNOWN_DIVERGENT_COMPONENTS = frozenset(
    {
        ("cloud", "schemas", "OTelBundleRequest"),
        ("cloud", "schemas", "OTelCollectorProtocolConfig"),
    }
)

# Editions ranked from least to most feature-complete. When two editions describe the same
# endpoint identically except for its permission documentation, the higher-ranked edition's
# copy wins: permissions declared via ``OkayToIgnorePerm`` only render in editions where the
# component owning them is present (e.g. custom graphs in the commercial editions), so the
# higher-ranked edition carries the most complete documentation.
_EDITION_RANK: Mapping[str, int] = {
    Edition.COMMUNITY.long: 0,
    Edition.CLOUD.long: 1,
    Edition.PRO.long: 2,
    Edition.ULTIMATE.long: 3,
    Edition.ULTIMATEMT.long: 4,
}


def _differ_only_in_description(first: object, second: object) -> bool:
    """Return whether two operation objects are equal apart from their ``description``."""
    if not (isinstance(first, Mapping) and isinstance(second, Mapping)):
        return False
    if set(first) != set(second):
        return False
    return all(key == "description" or first[key] == second[key] for key in first)


class MergeConflictError(Exception):
    def __init__(
        self,
        location: str,
        first_edition: str,
        second_edition: str,
        first: object,
        second: object,
    ) -> None:
        diff = "\n".join(
            difflib.unified_diff(
                json.dumps(first, indent=2, sort_keys=True, default=str).splitlines(),
                json.dumps(second, indent=2, sort_keys=True, default=str).splitlines(),
                fromfile=first_edition,
                tofile=second_edition,
                lineterm="",
            )
        )
        super().__init__(
            f"{location} differs between the {first_edition} and {second_edition} editions:\n{diff}"
        )


class _Missing:
    @override
    def __str__(self) -> str:
        return "<missing>"


_MISSING = _Missing()


def merge_specs(
    specs: Mapping[str, Mapping[str, object]],
    *,
    divergent_paths: Set[tuple[str, str, str]] = frozenset(),
    divergent_components: Set[tuple[str, str, str]] = frozenset(),
) -> dict[str, object]:
    """Merge per-edition specs, raising MergeConflictError on unexpected divergence.

    Divergence entries are (edition, method, path) / (edition, section, name) tuples; the
    tagged edition's copy is dropped and must exist whenever that edition is merged.
    """
    known_editions = {edition.long for edition in Edition}
    if unknown_editions := set(specs) - known_editions:
        raise ValueError(f"Unknown editions: {sorted(unknown_editions)}")
    if (
        unknown_tags := {entry[0] for entry in divergent_paths | divergent_components}
        - known_editions
    ):
        raise ValueError(f"Unknown editions in divergence entries: {sorted(unknown_tags)}")

    pending_paths = {entry for entry in divergent_paths if entry[0] in specs}
    pending_components = {entry for entry in divergent_components if entry[0] in specs}

    metadata: dict[str, object] = {}
    paths: dict[str, dict[str, object]] = {}
    components: dict[str, dict[str, object]] = {}
    tags: dict[str, object] = {}
    tag_groups: dict[str, list[str]] = {}
    origin: dict[tuple[str, ...], str] = {}

    def merge_entry(
        container: dict[str, object],
        key: str,
        value: object,
        edition: str,
        location: tuple[str, ...],
    ) -> None:
        if key not in container:
            container[key] = value
            origin[location] = edition
        elif container[key] != value:
            raise MergeConflictError(
                "/".join(location), origin[location], edition, container[key], value
            )

    def merge_operation(path: str, method: str, operation: object, edition: str) -> None:
        location = ("paths", path, method)
        methods = paths.setdefault(path, {})
        if method not in methods:
            methods[method] = operation
            origin[location] = edition
        elif methods[method] == operation:
            pass
        elif _differ_only_in_description(methods[method], operation):
            # Edition-dependent permission documentation only; keep the higher-ranked copy.
            if _EDITION_RANK[edition] > _EDITION_RANK[origin[location]]:
                methods[method] = operation
                origin[location] = edition
        else:
            raise MergeConflictError(
                "/".join(location), origin[location], edition, methods[method], operation
            )

    ordered = [(edition, specs[edition]) for edition in sorted(specs)]
    metadata_keys = {key for _, spec in ordered for key in spec} - {
        "paths",
        "components",
        "tags",
        "x-tagGroups",
    }
    for edition, spec in ordered:
        for key in metadata_keys:
            merge_entry(metadata, key, spec.get(key, _MISSING), edition, (key,))
        for path, path_item in _as_mapping(spec.get("paths", {}), f"{edition}: paths").items():
            for method, operation in _as_mapping(path_item, f"{edition}: paths/{path}").items():
                if (edition, method, path) in divergent_paths:
                    pending_paths.discard((edition, method, path))
                    continue
                merge_operation(path, method, operation, edition)
        for section, entries in _as_mapping(
            spec.get("components", {}), f"{edition}: components"
        ).items():
            for name, value in _as_mapping(entries, f"{edition}: components/{section}").items():
                if (edition, section, name) in divergent_components:
                    pending_components.discard((edition, section, name))
                    continue
                merge_entry(
                    components.setdefault(section, {}),
                    name,
                    value,
                    edition,
                    ("components", section, name),
                )
        for tag in _as_sequence(spec.get("tags", []), f"{edition}: tags"):
            tag_name = _as_str(_as_mapping(tag, f"{edition}: tags")["name"], f"{edition}: tags")
            merge_entry(tags, tag_name, tag, edition, ("tags", tag_name))
        for group in _as_sequence(spec.get("x-tagGroups", []), f"{edition}: x-tagGroups"):
            group_mapping = _as_mapping(group, f"{edition}: x-tagGroups")
            group_name = _as_str(group_mapping["name"], f"{edition}: x-tagGroups")
            members = tag_groups.setdefault(group_name, [])
            location = f"{edition}: x-tagGroups/{group_name}"
            for member in _as_sequence(group_mapping["tags"], location):
                if member not in members:
                    members.append(_as_str(member, location))

    if pending_paths or pending_components:
        raise ValueError(
            "Expected divergences were not encountered, clean up the divergence entries: "
            + ", ".join(repr(entry) for entry in sorted(pending_paths | pending_components))
        )

    merged = dict(metadata)
    merged["paths"] = paths
    merged["components"] = components
    merged["tags"] = list(tags.values())
    merged["x-tagGroups"] = [
        {"name": name, "tags": members} for name, members in tag_groups.items()
    ]
    return {key: _sort_mapping_keys(merged[key]) for key in sorted(merged)}


def _as_mapping(value: object, location: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location}: expected a mapping, got {type(value).__name__}")
    return value


def _as_sequence(value: object, location: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError(f"{location}: expected a list, got {type(value).__name__}")
    return value


def _as_str(value: object, location: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{location}: expected a string, got {type(value).__name__}")
    return value


def _sort_mapping_keys(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _sort_mapping_keys(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, list):
        return [_sort_mapping_keys(item) for item in value]
    return value


def _parse_inputs(values: list[str]) -> dict[str, Path]:
    known_editions = {edition.long for edition in Edition}
    inputs: dict[str, Path] = {}
    for value in values:
        edition, separator, path = value.partition("=")
        if not separator or edition not in known_editions:
            raise SystemExit(f"Invalid --input {value!r}, expected <edition>=<spec file>")
        if edition in inputs:
            raise SystemExit(f"Duplicate --input for edition {edition}")
        inputs[edition] = Path(path)
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        dest="inputs",
        metavar="EDITION=SPEC_FILE",
        help="Edition name and path of its spec file, may be given multiple times",
    )
    parser.add_argument("--out", required=True, type=Path, help="Target file")
    args = parser.parse_args()

    specs = {
        edition: _as_mapping(yaml.safe_load(path.read_text()), str(path))
        for edition, path in _parse_inputs(args.inputs).items()
    }
    merged = merge_specs(
        specs,
        divergent_paths=_KNOWN_DIVERGENT_PATHS,
        divergent_components=_KNOWN_DIVERGENT_COMPONENTS,
    )
    args.out.write_text(yaml.safe_dump(merged, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
