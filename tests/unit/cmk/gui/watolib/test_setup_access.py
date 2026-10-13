#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager
from typing import override

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.customer import (
    ABCCustomerAPI,
    customer_api_registry,
    CustomerAPIStub,
    CustomerId,
    CustomerIdOrGlobal,
    SCOPE_GLOBAL,
)
from cmk.gui.watolib.setup_access import ensure_provider_site, ensure_setup_enabled


class _SiteOfACustomer(CustomerAPIStub):
    """Multi-tenancy as an edition with customers implements it."""

    site_customer: CustomerId = "customer_a"

    @classmethod
    @override
    def current_customer(cls, config: Config) -> CustomerIdOrGlobal:
        return cls.site_customer

    @classmethod
    @override
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return customer_id is SCOPE_GLOBAL

    @classmethod
    @override
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return customer_id == "provider"


class _SiteOfTheProvider(_SiteOfACustomer):
    site_customer = "provider"


@contextmanager
def _customer_api_of_local_site(
    api: type[ABCCustomerAPI], local_edition: Edition
) -> Iterator[None]:
    ident = str(local_edition)
    previous = customer_api_registry[ident]
    customer_api_registry.register(api(ident))
    try:
        yield
    finally:
        customer_api_registry.register(previous)


def test_disabled_setup_is_refused(load_config: Config) -> None:
    with pytest.raises(MKGeneralException):
        ensure_setup_enabled(dataclasses.replace(load_config, wato_enabled=False))


def test_enabled_setup_is_reachable(load_config: Config) -> None:
    ensure_setup_enabled(dataclasses.replace(load_config, wato_enabled=True))


def test_the_site_of_a_customer_is_refused(
    load_config: Config,
    test_edition: Edition,
) -> None:
    with (
        _customer_api_of_local_site(_SiteOfACustomer, test_edition),
        pytest.raises(MKGeneralException),
    ):
        ensure_provider_site(load_config)


def test_the_site_of_the_provider_is_reachable(
    load_config: Config,
    test_edition: Edition,
) -> None:
    with _customer_api_of_local_site(_SiteOfTheProvider, test_edition):
        ensure_provider_site(load_config)


def test_a_site_without_customers_is_reachable(
    load_config: Config,
    test_edition: Edition,
) -> None:
    with _customer_api_of_local_site(CustomerAPIStub, test_edition):
        ensure_provider_site(load_config)
