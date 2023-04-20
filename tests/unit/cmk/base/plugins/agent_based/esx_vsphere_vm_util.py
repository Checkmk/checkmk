#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.utils import esx_vsphere


class ESXVMFactory(ModelFactory):
    __model__ = esx_vsphere.ESXVm


def esx_vm_section(**kwargs) -> esx_vsphere.ESXVm:  # type: ignore[no-untyped-def]
    return ESXVMFactory.build(**kwargs)
