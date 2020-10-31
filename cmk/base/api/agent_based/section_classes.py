#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for section plugins
"""
from cmk.utils.type_defs import SNMPDetectBaseType


class SNMPDetectSpecification(SNMPDetectBaseType):
    """A specification for SNMP device detection

    Note that the structure of this object is not part of the API,
    and may change at any time.
    """
    # This class is only part of the check *API*, in the sense that it hides
    # the SNMPDetectBaseType from the user (and from the auto generated doc!).
    # Use it for type annotations API frontend objects
