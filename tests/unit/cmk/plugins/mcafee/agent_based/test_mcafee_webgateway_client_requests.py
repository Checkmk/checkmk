#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, SimpleSNMPSection, State, StringTable
from cmk.plugins.mcafee.agent_based import mcafee_webgateway_client_requests as plugin
from cmk.plugins.mcafee.libgateway import MISC_DEFAULT_PARAMS, MiscParams

WALK_MCAFEE: dict[str, str] = {
    ".1.3.6.1.2.1.1.1.0": "McAfee Web Gateway 7;VMWare;VMware, Inc.",
    ".1.3.6.1.4.1.1230.2.7.2.2.1.0": "96919",
    ".1.3.6.1.4.1.1230.2.7.2.3.1.0": "1063172",
    ".1.3.6.1.4.1.1230.2.7.2.6.1.0": "92114",
}

WALK_SKYHIGH: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.59732.2.7.1.1",
    ".1.3.6.1.4.1.59732.2.7.2.2.1.0": "96919",
    ".1.3.6.1.4.1.59732.2.7.2.3.1.0": "1063172",
    ".1.3.6.1.4.1.59732.2.7.2.6.1.0": "92114",
}

TABLE_CR: StringTable = [["96919", "1063172", "92114"]]


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (WALK_MCAFEE, plugin.snmp_section_mcafee_webgateway_client_requests),
        (WALK_SKYHIGH, plugin.snmp_section_skyhigh_security_webgateway_client_requests),
    ],
)
def test_detect(
    walk: dict[str, str],
    detected_section: SimpleSNMPSection,
) -> None:
    assert evaluate_snmp_detection(detect_spec=detected_section.detect, oid_value_getter=walk.get)


@pytest.mark.parametrize(
    "detected_section",
    [
        plugin.snmp_section_mcafee_webgateway_client_requests,
        plugin.snmp_section_skyhigh_security_webgateway_client_requests,
    ],
)
def test_parse(detected_section: SimpleSNMPSection) -> None:
    # Act
    section = detected_section.parse_function([TABLE_CR])

    # Assert
    assert section is not None


@pytest.mark.parametrize(
    "detected_section",
    [
        plugin.snmp_section_mcafee_webgateway_client_requests,
        plugin.snmp_section_skyhigh_security_webgateway_client_requests,
    ],
)
def test_discovery(detected_section: SimpleSNMPSection) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_CR])
    assert section is not None

    # Act
    service_http = list(plugin.discovery_http(section))
    service_https = list(plugin.discovery_https(section))
    service_httpv2 = list(plugin.discovery_httpv2(section))

    # Assert
    assert service_http == [Service()]
    assert service_https == [Service()]
    assert service_httpv2 == [Service()]


@pytest.mark.parametrize(
    "detected_section, params, expected_results",
    [
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_https": None},
            [
                Result(state=State.OK, summary="2.0/s"),
                Metric("requests_per_second", 2.0),
            ],
            id="No levels",
        ),
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_https": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical",
        ),
        pytest.param(
            plugin.snmp_section_skyhigh_security_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_https": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical skyhigh",
        ),
    ],
)
def test_check_https(
    detected_section: SimpleSNMPSection,
    params: MiscParams,
    expected_results: list[object],
) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_CR])
    assert section is not None
    now = 2.0
    value_store = {"https": (1.0, 92112)}

    # Act
    results = list(plugin._check_https(now, value_store, params, section))

    # Assert
    assert results == expected_results


@pytest.mark.parametrize(
    "detected_section, params, expected_results",
    [
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_httpv2": None},
            [
                Result(state=State.OK, summary="2.0/s"),
                Metric("requests_per_second", 2.0),
            ],
            id="No levels",
        ),
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_httpv2": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical",
        ),
        pytest.param(
            plugin.snmp_section_skyhigh_security_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_httpv2": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical skyhigh",
        ),
    ],
)
def test_check_httpv2(
    detected_section: SimpleSNMPSection,
    params: MiscParams,
    expected_results: list[object],
) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_CR])
    assert section is not None
    now = 2.0
    value_store = {"httpv2": (1.0, 1063170)}

    # Act
    results = list(plugin._check_httpv2(now, value_store, params, section))

    # Assert
    assert results == expected_results


@pytest.mark.parametrize(
    "detected_section, params, expected_results",
    [
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_http": None},
            [
                Result(state=State.OK, summary="2.0/s"),
                Metric("requests_per_second", 2.0),
            ],
            id="No levels",
        ),
        pytest.param(
            plugin.snmp_section_mcafee_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_http": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical",
        ),
        pytest.param(
            plugin.snmp_section_skyhigh_security_webgateway_client_requests,
            MISC_DEFAULT_PARAMS | {"client_requests_http": (1, 2)},
            [
                Result(state=State.CRIT, summary="2.0/s (warn/crit at 1.0/s/2.0/s)"),
                Metric("requests_per_second", 2.0, levels=(1.0, 2.0)),
            ],
            id="Critical skyhigh",
        ),
    ],
)
def test_check_http(
    detected_section: SimpleSNMPSection,
    params: MiscParams,
    expected_results: list[object],
) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_CR])
    assert section is not None
    now = 2.0
    value_store = {"http": (1.0, 96917)}

    # Act
    results = list(plugin._check_http(now, value_store, params, section))

    # Assert
    assert results == expected_results


@pytest.mark.parametrize(
    "detected_section",
    [
        plugin.snmp_section_mcafee_webgateway_client_requests,
        plugin.snmp_section_skyhigh_security_webgateway_client_requests,
    ],
)
def test_check_results_newly_discovered(detected_section: SimpleSNMPSection) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_CR])
    assert section is not None

    # Act
    results_http = list(plugin._check_http(2.0, {}, MISC_DEFAULT_PARAMS, section))
    results_https = list(plugin._check_https(2.0, {}, MISC_DEFAULT_PARAMS, section))
    results_httpv2 = list(plugin._check_httpv2(2.0, {}, MISC_DEFAULT_PARAMS, section))

    # Assert
    assert results_http == [Result(state=State.OK, summary="Can't compute rate.")]
    assert results_https == [Result(state=State.OK, summary="Can't compute rate.")]
    assert results_httpv2 == [Result(state=State.OK, summary="Can't compute rate.")]
