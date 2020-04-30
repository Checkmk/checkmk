#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Abstract classes and types."""

import abc
from typing import Optional

import six

from cmk.utils.type_defs import (
    CheckPluginName,
    ContextName,
    OID,
    RawValue,
    SNMPRowInfo,
    SNMPHostConfig,
)

__all__ = ["ABCSNMPBackend"]


class ABCSNMPBackend(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def get(self, snmp_config, oid, context_name=None):
        # type: (SNMPHostConfig, OID, Optional[ContextName]) -> Optional[RawValue]
        """Fetch a single OID from the given host in the given SNMP context

        The OID may end with .* to perform a GETNEXT request. Otherwise a GET
        request is sent to the given host.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def walk(self,
             snmp_config,
             oid,
             check_plugin_name=None,
             table_base_oid=None,
             context_name=None):
        # type: (SNMPHostConfig, OID, Optional[CheckPluginName], Optional[OID], Optional[ContextName]) -> SNMPRowInfo
        return []
