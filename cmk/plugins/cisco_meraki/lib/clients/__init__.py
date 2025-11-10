#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Protocol, Self

from ._organizations import OrganizationsClient, OrganizationsSDK


class OrganizationSDK(
    OrganizationsSDK,
): ...


class MerakiSDK(Protocol):
    organizations: OrganizationSDK


@dataclass(frozen=True, kw_only=True)
class MerakiClients:
    organizations: OrganizationsClient

    @classmethod
    def build(cls, sdk: MerakiSDK) -> Self:
        return cls(
            organizations=OrganizationsClient(sdk.organizations),
        )


__all__ = ["MerakiClients"]
