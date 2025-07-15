#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.common.repo import is_enterprise_repo
from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.valuespec import autocompleter_registry


@pytest.fixture(name="expected_autocompleters")
def fixture_expected_autocompleters() -> list[str]:
    # ATTENTION! The Checkmk Grafana plugin requires the following autocompletes!
    # Please contact the grafana component members before removing one from this list!
    autocompleters = [
        "sites",
        "monitored_hostname",
        "allgroups",
        "label",
        "tag_groups",
        "tag_groups_opt",
        "monitored_service_description",
    ]

    if is_enterprise_repo():
        autocompleters.append("graph_template_for_combined_graph")
        autocompleters.append("combined_graphs")
        # Please read the comment above!

    return autocompleters


def test_openapi_autocompleter_functions_exist(expected_autocompleters: list[str]) -> None:
    registered_autocompleters = autocompleter_registry.keys()
    for autocomplete_name in expected_autocompleters:
        assert autocomplete_name in registered_autocompleters


def test_openapi_autocompleter_does_not_exist(clients: ClientRegistry) -> None:
    clients.AutoComplete.invoke(
        "I_do_not_exist", value="", parameters={}, expect_ok=False
    ).assert_status_code(404)


def test_openapi_sites_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])

    with mock_livestatus(expect_status_query=True):
        clients.AutoComplete.invoke("sites", {"strict": False, "context": {}}, "")


def test_openapi_all_groups_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])

    mock_livestatus.expect_query("GET hostgroups\nColumns: name alias\n")

    with mock_livestatus(expect_status_query=True):
        clients.AutoComplete.invoke(
            "allgroups", {"group_type": "host", "strict": True, "context": {}}, ""
        )


def test_openapi_tag_groups_autocompleter(clients: ClientRegistry) -> None:
    clients.AutoComplete.invoke("tag_groups", {"strict": True, "context": {}}, "")


def test_openapi_tag_groups_opt_autocompleter(clients: ClientRegistry) -> None:
    clients.AutoComplete.invoke("tag_groups_opt", {"strict": True, "group_id": ""}, "")


def test_openapi_monitored_hostname_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])

    mock_livestatus.expect_query(
        "GET hosts\nColumns: host_name\nFilter: host_name ... .\nColumnHeaders: off\nLimit: 201\n",
        match_type="ellipsis",
    )

    with mock_livestatus(expect_status_query=True):
        clients.AutoComplete.invoke(
            "monitored_hostname", {"strict": "with_source", "context": {}}, ""
        )


def test_openapi_monitored_service_description_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])

    mock_livestatus.expect_query(
        "GET services\nColumns: service_description\nFilter: service_description ~~ .\nColumnHeaders: off\nLimit: 201\n"
    )

    with mock_livestatus(expect_status_query=True):
        clients.AutoComplete.invoke(
            "monitored_service_description", {"strict": True, "context": {}}, ""
        )


def test_openapi_lenny_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])

    mock_livestatus.add_table("labels", [{"name": "lenny", "value": "( ͡° ͜ʖ ͡°)"}])
    mock_livestatus.expect_query("GET labels\nColumns: name value\n")

    with mock_livestatus(expect_status_query=True):
        clients.AutoComplete.invoke("label", {"world": "core", "context": {}}, "")


@pytest.mark.skipif(
    not is_enterprise_repo(),
    reason="graph_template_for_combined_graph is not available in CRE",
)
def test_openapi_graph_template_for_combined_graph_autocompleter(clients: ClientRegistry) -> None:
    clients.AutoComplete.invoke(
        "graph_template_for_combined_graph",
        {"strict": True},
        "",
    )


@pytest.mark.skipif(
    not is_enterprise_repo(),
    reason="combined_graphs is not available in CRE",
)
def test_openapi_combined_graphs_autocompleter(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    # this is needed for the checkmk grafana plugin. please get in touch with the component members
    # if you have to adapt this test.
    clients.AutoComplete.invoke(
        "combined_graphs",
        {
            "presentation": "lines",
            "mode": "metric",
            "datasource": "services",
            "single_infos": ["host"],
            "context": {},
        },
    )
