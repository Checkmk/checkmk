#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, override

from livestatus import SiteConfigurations

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition

from cmk.utils import paths

from cmk.gui.groups import GroupSpec
from cmk.gui.hooks import request_memoize
from cmk.gui.valuespec import DropdownChoice, ValueSpec

CustomerId = str
SCOPE_GLOBAL = None
# TODO: Encoding SCOPE_GLOBAL as is a very bad idea from a typing point of
# view: Very often we can't be sure if we see None or a real CustomerId.
CustomerIdOrGlobal = CustomerId | None


class ABCCustomerAPI(ABC):
    def __init__(self, ident: str):
        self.ident = ident

    @classmethod
    @abstractmethod
    def get_sites_of_customer(cls, customer_id: CustomerId) -> SiteConfigurations: ...

    @classmethod
    @abstractmethod
    def get_customer_id(cls, the_object: Mapping[str, Any]) -> CustomerIdOrGlobal: ...

    @classmethod
    @abstractmethod
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool: ...

    @classmethod
    @abstractmethod
    def customer_group_sites(cls, group: GroupSpec) -> Sequence[SiteId] | None: ...

    @classmethod
    @abstractmethod
    def get_customer_name_by_id(cls, customer_id: CustomerIdOrGlobal) -> str: ...

    @classmethod
    @abstractmethod
    def get_customer_name(cls, the_object: Mapping[str, Any]) -> str: ...

    @classmethod
    @abstractmethod
    def vs_customer(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> DropdownChoice: ...

    @classmethod
    @abstractmethod
    def default_customer_id(cls) -> CustomerId:
        return ""

    @classmethod
    @abstractmethod
    def customer_choice_element(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> list[tuple[str, ValueSpec]]: ...

    @classmethod
    @abstractmethod
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool: ...

    @classmethod
    @abstractmethod
    def is_current_customer(cls, customer_id: CustomerIdOrGlobal) -> bool: ...

    @classmethod
    @abstractmethod
    def customer_collection(cls) -> list[CustomerIdOrGlobal]: ...


class CustomerAPIStub(ABCCustomerAPI):
    @override
    @classmethod
    def get_sites_of_customer(cls, customer_id: CustomerId) -> SiteConfigurations:
        return SiteConfigurations({})

    @override
    @classmethod
    def get_customer_id(cls, the_object: Mapping[str, Any]) -> CustomerIdOrGlobal:
        return SCOPE_GLOBAL

    @override
    @classmethod
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return True

    @override
    @classmethod
    def customer_group_sites(cls, group: GroupSpec) -> Sequence[SiteId] | None:
        return None

    @override
    @classmethod
    def get_customer_name_by_id(cls, customer_id: CustomerIdOrGlobal) -> str:
        return str(customer_id)

    @override
    @classmethod
    def get_customer_name(cls, the_object: Mapping[str, Any]) -> str:
        return ""

    @override
    @classmethod
    def vs_customer(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> DropdownChoice:
        return DropdownChoice(choices=[])

    @override
    @classmethod
    def default_customer_id(cls) -> CustomerId:
        return ""

    @override
    @classmethod
    def customer_choice_element(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> list[tuple[str, ValueSpec]]:
        return []

    @override
    @classmethod
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return False

    @override
    @classmethod
    def is_current_customer(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return False

    @override
    @classmethod
    def customer_collection(cls) -> list[CustomerIdOrGlobal]:
        return []


@request_memoize()
def customer_api() -> ABCCustomerAPI:
    return customer_api_registry[str(edition(paths.omd_root))]


class CustomerAPIRegistry(Registry[ABCCustomerAPI]):
    @override
    def plugin_name(self, instance: ABCCustomerAPI) -> str:
        return instance.ident


customer_api_registry = CustomerAPIRegistry()
