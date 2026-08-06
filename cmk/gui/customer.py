#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, override

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.gui.groups import GroupSpec
from cmk.gui.hooks import request_memoize
from cmk.gui.type_defs import UserSpec
from cmk.gui.valuespec import DropdownChoice, ValueSpec
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils import paths

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
    def customer_choice_form_spec(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> list[tuple[str, FormSpec]]: ...

    @classmethod
    @abstractmethod
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool: ...

    @classmethod
    @abstractmethod
    def is_current_customer(cls, customer_id: CustomerIdOrGlobal) -> bool: ...

    @classmethod
    @abstractmethod
    def customer_collection(cls) -> list[CustomerIdOrGlobal]: ...

    @classmethod
    @abstractmethod
    def set_customer_for_user(cls, user: UserSpec, customer_id: CustomerId | None) -> None:
        """Scope a user created by a connection to the connection's customer.

        The user's customer decides which sites the user is synchronized to. Users of a
        globally scoped connection (``customer_id`` is ``None``) are assigned the
        provider customer. Editions without multi-tenancy leave the user untouched.
        """


class CustomerAPIStub(ABCCustomerAPI):
    @classmethod
    @override
    def get_sites_of_customer(cls, customer_id: CustomerId) -> SiteConfigurations:
        return SiteConfigurations({})

    @classmethod
    @override
    def get_customer_id(cls, the_object: Mapping[str, Any]) -> CustomerIdOrGlobal:
        return SCOPE_GLOBAL

    @classmethod
    @override
    def is_global(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return True

    @classmethod
    @override
    def customer_group_sites(cls, group: GroupSpec) -> Sequence[SiteId] | None:
        return None

    @classmethod
    @override
    def get_customer_name_by_id(cls, customer_id: CustomerIdOrGlobal) -> str:
        return str(customer_id)

    @classmethod
    @override
    def get_customer_name(cls, the_object: Mapping[str, Any]) -> str:
        return ""

    @classmethod
    @override
    def vs_customer(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> DropdownChoice:
        return DropdownChoice(choices=[])

    @classmethod
    @override
    def default_customer_id(cls) -> CustomerId:
        return ""

    @classmethod
    @override
    def customer_choice_element(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> list[tuple[str, ValueSpec]]:
        return []

    @classmethod
    @override
    def customer_choice_form_spec(
        cls, deflt: CustomerId | None = None, with_global: bool = True
    ) -> list[tuple[str, FormSpec]]:
        return []

    @classmethod
    @override
    def is_provider(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return False

    @classmethod
    @override
    def is_current_customer(cls, customer_id: CustomerIdOrGlobal) -> bool:
        return False

    @classmethod
    @override
    def customer_collection(cls) -> list[CustomerIdOrGlobal]:
        return []

    @classmethod
    @override
    def set_customer_for_user(cls, user: UserSpec, customer_id: CustomerId | None) -> None:
        pass


@request_memoize()
def customer_api() -> ABCCustomerAPI:
    return customer_api_registry[str(edition(paths.omd_root))]


class CustomerAPIRegistry(Registry[ABCCustomerAPI]):
    @override
    def plugin_name(self, instance: ABCCustomerAPI) -> str:
        return instance.ident


customer_api_registry = CustomerAPIRegistry()
