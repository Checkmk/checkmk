#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from typing import Protocol

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.specs.exitspec import ExitSpec
from cmk.ruleset_matcher.labels import LabelManager
from cmk.ruleset_matcher.matcher import RulesetMatcher


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: dict[str, ExitSpec]


class ExitCodeSpec(Protocol):
    def __call__(self, hostname: HostName, data_source_id: str | None = None) -> ExitSpec: ...


def make_exit_code_spec(
    loaded_config: BaseConfig,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> ExitCodeSpec:
    """Create a callback that returns the exit code spec for a host / data source."""

    def exit_code_spec(hostname: HostName, data_source_id: str | None = None) -> ExitSpec:
        spec: _NestedExitSpec = {}
        # TODO: Can we use get_host_merged_dict?
        specs = matcher.get_host_values_all(
            hostname, loaded_config.check_mk_exit_status, label_manager.labels_of_host
        )
        for entry in specs[::-1]:
            spec.update(entry)

        merged_spec = _extract_data_source_exit_code_spec(spec, data_source_id)
        return _merge_with_optional_exit_code_parameters(spec, merged_spec)

    return exit_code_spec


def _extract_data_source_exit_code_spec(
    spec: _NestedExitSpec,
    data_source_id: str | None,
) -> ExitSpec:
    if data_source_id is not None:
        with contextlib.suppress(KeyError):
            return spec["individual"][data_source_id]
    with contextlib.suppress(KeyError):
        return spec["overall"]
    # Old configuration format
    return spec


def _merge_with_optional_exit_code_parameters(
    spec: _NestedExitSpec,
    merged_spec: ExitSpec,
) -> ExitSpec:
    # Additional optional parameters which are not part of individual
    # or overall parameters
    if (value := spec.get("restricted_address_mismatch")) is not None:
        merged_spec["restricted_address_mismatch"] = value
    if (value := spec.get("legacy_pull_mode")) is not None:
        merged_spec["legacy_pull_mode"] = value
    return merged_spec
