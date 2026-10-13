#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.update_config.internal import PreUpdateAction as PreUpdateAction
from cmk.update_config.internal import UpdateAction as UpdateAction


class UpdateActionRegistry(Registry[UpdateAction]):
    @override
    def plugin_name(self, instance: UpdateAction) -> str:
        return instance.name


update_action_registry = UpdateActionRegistry()


class PreUpdateActionRegistry(Registry[PreUpdateAction]):
    @override
    def plugin_name(self, instance: PreUpdateAction) -> str:
        return instance.name


pre_update_action_registry = PreUpdateActionRegistry()
