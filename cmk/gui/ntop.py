#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""ntop integration interface for generic GUI code.

The real implementation lives in cmk.gui.nonfree.pro.ntop and is registered at
startup.  Generic (edition-independent) code uses the accessor function
``ntop_connection()`` which returns the stub when the feature is absent.
"""

from abc import ABC, abstractmethod
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import edition
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import NtopConnectionSpec
from cmk.utils import paths


class NtopConnectionInterface(ABC):
    def __init__(self, ident: str) -> None:
        self.ident = ident

    @abstractmethod
    def get_connection(self) -> NtopConnectionSpec | None: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def is_active(self) -> bool: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def get_misconfiguration_reason(self) -> str: ...

    @abstractmethod
    def use_host_filter(self) -> bool: ...


class NtopConnectionStub(NtopConnectionInterface):
    """Null implementation for editions without ntop."""

    def get_connection(self) -> None:
        return None

    def is_available(self) -> bool:
        return False

    def is_active(self) -> bool:
        return False

    def is_configured(self) -> bool:
        return False

    def get_misconfiguration_reason(self) -> str:
        return _("ntopng integration is only available in CEE")

    def use_host_filter(self) -> bool:
        return True


class NtopConnectionRegistry(Registry[NtopConnectionInterface]):
    @override
    def plugin_name(self, instance: NtopConnectionInterface) -> str:
        return instance.ident


ntop_connection_registry = NtopConnectionRegistry()


@request_memoize()
def ntop_connection() -> NtopConnectionInterface:
    return ntop_connection_registry[str(edition(paths.omd_root))]
