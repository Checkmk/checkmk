#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from livestatus import SiteConfigurations, SiteId

from cmk.gui.groups import GroupSpec
from cmk.gui.hooks import request_memoize

CustomerId = str
SCOPE_GLOBAL = None
# TODO: Encoding SCOPE_GLOBAL as is a very bad idea from a typing point of
# view: Very often we can't be sure if we see None or a real CustomerId.
CustomerIdOrGlobal = CustomerId | None


class ABCCustomerAPI(ABC):
    @classmethod
    @abstractmethod
    def get_sites_of_customer(cls, customer_id: CustomerId) -> SiteConfigurations:
        ...

    @classmethod
    @abstractmethod
    def get_customer_id(cls, the_object: Mapping[str, Any]) -> CustomerIdOrGlobal:
        ...

    @classmethod
    @abstractmethod
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        ...

    @classmethod
    @abstractmethod
    def customer_group_sites(cls, group: GroupSpec) -> Sequence[SiteId] | None:
        ...

    @classmethod
    @abstractmethod
    def get_customer_name_by_id(cls, customer_id: CustomerIdOrGlobal) -> str:
        ...


class CustomerAPIStub(ABCCustomerAPI):
    @classmethod
    def get_sites_of_customer(cls, customer_id: CustomerId) -> SiteConfigurations:
        return SiteConfigurations({})

    @classmethod
    def get_customer_id(cls, the_object: Mapping[str, Any]) -> CustomerIdOrGlobal:
        return SCOPE_GLOBAL

    @classmethod
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return True

    @classmethod
    def customer_group_sites(cls, group: GroupSpec) -> Sequence[SiteId] | None:
        return None

    @classmethod
    def get_customer_name_by_id(cls, customer_id: CustomerIdOrGlobal) -> str:
        return str(customer_id)


@request_memoize()
def customer_api() -> ABCCustomerAPI:
    return CustomerAPIClass()


CustomerAPIClass: type[ABCCustomerAPI] = CustomerAPIStub
