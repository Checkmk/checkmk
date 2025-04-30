#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.plugin_registry import Registry

from ._base import UserConnector


class UserConnectorRegistry(Registry[type[UserConnector]]):
    """The management object for all available user connector classes.

    Have a look at the base class for details."""

    @override
    def plugin_name(self, instance: type[UserConnector]) -> str:
        return instance.type()


user_connector_registry = UserConnectorRegistry()
