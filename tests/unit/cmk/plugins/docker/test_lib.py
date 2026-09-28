#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.docker.lib import (
    cleanup_oci_error_message,
    get_short_id,
    MemorySection,
    parse,
    parse_multiline,
)


def test_parse_strict() -> None:
    result = parse(
        [
            [
                "@docker_version_info",
                '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
            ],
            ['{"payload": 1}'],
        ]
    )
    assert result.version == {
        "PluginVersion": "0.1",
        "DockerPyVersion": "4.1.0",
        "ApiVersion": "1.41",
    }
    assert result.data == {"payload": 1}


@pytest.mark.parametrize(
    "data, expected",
    [
        ([["@docker_version_info", "{}"], ["1", "2"]], 1),  # 2 should not be there
        ([["@docker_version_info", "{}", "2"], ["1"]], 1),  # 2 should not be there
        ([["@docker_version_info", "{}"], ["1"], ["2"]], 1),  # 2 should not be there
    ],
)
def test_parse_strict_violation(data: StringTable, expected: Mapping[str, object]) -> None:
    with pytest.raises(ValueError):
        parse(data)
    assert parse(data, strict=False).data == expected


def test_parse_strict_empty_version() -> None:
    result = parse([["@docker_version_info", "{}"], ['{"payload": 1}']])
    assert result.version == {}
    assert result.data == {"payload": 1}


def test_parse_multiline() -> None:
    result = parse_multiline(
        [["@docker_version_info", "{}"], ['{"value": 1}'], ['{"value": 2}'], ['{"value": 3}']]
    )
    assert result.version == {}
    assert list(result.data) == [{"value": 1}, {"value": 2}, {"value": 3}]


def test_parse_multiline_skips_null_lines() -> None:
    result = parse_multiline(
        [["@docker_version_info", "{}"], ['{"value": 1}'], ["null"], ['{"value": 2}']]
    )
    assert list(result.data) == [{"value": 1}, {"value": 2}]


@pytest.mark.parametrize(
    "data_in, data_out",
    [
        (
            [],
            [],
        ),
        (
            [["1"]],
            [["1"]],
        ),
        (
            [["1", "2"]],
            [["1", "2"]],
        ),
        (
            # this is the original error message
            [
                ["1", "2"],
                [
                    (
                        "OCI runtime exec failed: exec failed: container_linux.go:344: starting container "
                        'process caused "exec: "check_mk_agent": executable file not found in $PATH": unknown'
                    )
                ],
            ],
            [["1", "2"]],
        ),
        (
            # this is the prefix it is tested with
            [["1", "2"], ["OCI runtime exec failed: exec failed:"]],
            [["1", "2"]],
        ),
        (
            # only replace if last element is of size 1
            [["1", "2"], ["1", "OCI runtime exec failed: exec failed:"]],
            [["1", "2"], ["1", "OCI runtime exec failed: exec failed:"]],
        ),
    ],
)
def test_parse_remove_error_message(data_in: StringTable, data_out: StringTable) -> None:
    cleaned_up = cleanup_oci_error_message(data_in)
    assert cleaned_up == data_out


@pytest.mark.parametrize(
    "memory_section, result",
    [
        [
            MemorySection(mem_total=16, mem_usage=3, mem_cache=0),
            {"MemFree": 16 - 3, "MemTotal": 16},
        ],
        [MemorySection(mem_total=16, mem_usage=3, mem_cache=4), {"MemFree": 16, "MemTotal": 16}],
    ],
)
def test_to_mem_used(memory_section: MemorySection, result: dict[str, int]) -> None:
    assert memory_section.to_mem_used() == result


@pytest.mark.parametrize(
    "indata,expected",
    [
        (
            "docker-pullable://nginx@sha256:e3456c851a152494c3e4ff5fcc26f240206abac0c9d794affb40e0714846c451",
            "e3456c851a15",
        ),
    ],
)
def test_parse_short_id(indata: str, expected: str) -> None:
    actual = get_short_id(indata)
    assert actual == expected
