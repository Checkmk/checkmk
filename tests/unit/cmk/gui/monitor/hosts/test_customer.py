#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import cast

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.customer import CustomerIdOrGlobal, SCOPE_GLOBAL
from cmk.gui.monitor.hosts._customer import customer_resolver
from cmk.livestatus_client import SiteConfigurations

_SITES = cast(
    SiteConfigurations,
    {
        SiteId("central"): {},
        SiteId("remote_a"): {"customer": "customer_a"},
    },
)

_CUSTOMER_NAMES = {"provider": "Provider", "customer_a": "Customer A", "customer_b": "Customer B"}


class _MultiTenancyCustomerAPI:
    """Stands in for the multi-tenancy customer API, which names the customer of a site."""

    @staticmethod
    def get_customer_id(the_object: Mapping[str, object]) -> CustomerIdOrGlobal:
        return cast(CustomerIdOrGlobal, the_object.get("customer", "provider"))

    @staticmethod
    def get_customer_name_by_id(customer_id: CustomerIdOrGlobal) -> str:
        return _CUSTOMER_NAMES.get(str(customer_id), f"({customer_id} - Customer name missing)")


@pytest.fixture(name="multi_tenancy")
def _multi_tenancy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.monitor.hosts._customer.customer_api", lambda: _MultiTenancyCustomerAPI
    )


@pytest.fixture(name="on_remote_site")
def _on_remote_site(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.gui.monitor.hosts._customer.is_distributed_setup_remote_site", lambda _sites: True
    )


@pytest.fixture(name="serving_customer")
def _serving_customer(request_context: None) -> Iterator[None]:
    """The customer a remote site is told it serves, as the synced configuration states it."""
    original = active_config._raw_config
    active_config._raw_config = {**original, "current_customer": "customer_b"}
    try:
        yield
    finally:
        active_config._raw_config = original


def _resolve(site_id: str, *, sites: SiteConfigurations = _SITES) -> str | None:
    return customer_resolver(sites=sites)(site_id)


@pytest.mark.usefixtures("multi_tenancy")
def test_a_host_is_named_for_the_customer_of_its_site() -> None:
    assert _resolve("remote_a") == "Customer A"


@pytest.mark.usefixtures("multi_tenancy")
def test_a_site_without_a_customer_belongs_to_the_provider() -> None:
    assert _resolve("central") == "Provider"


@pytest.mark.usefixtures("multi_tenancy")
def test_an_unknown_site_falls_back_to_the_provider() -> None:
    assert _resolve("gone") == "Provider"


@pytest.mark.usefixtures("multi_tenancy")
def test_a_customer_without_a_name_is_reported_as_such() -> None:
    sites = cast(SiteConfigurations, {SiteId("orphan"): {"customer": "vanished"}})

    assert _resolve("orphan", sites=sites) == "(vanished - Customer name missing)"


def test_editions_without_multi_tenancy_report_no_customer() -> None:
    """Their customer API stub reports the global scope, which is no customer at all."""
    assert SCOPE_GLOBAL is None
    assert _resolve("remote_a") is None


@pytest.mark.usefixtures("on_remote_site", "serving_customer", "multi_tenancy")
def test_a_remote_site_names_the_customer_it_serves() -> None:
    # A remote site is never synced the site list, so it cannot look its own customer up.
    assert _resolve("remote_a") == "Customer B"


@pytest.mark.usefixtures("on_remote_site", "request_context")
def test_a_remote_site_without_multi_tenancy_reports_no_customer() -> None:
    assert _resolve("remote_a") is None
