#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains the entry points to the core helpers from base.

The sources configure and instantiate the helpers and then
delegate to them.

The general design is

.. uml::

    abstract Source {
        fetch() : RawData
        parse(RawData) : HostSections
        summarize(HostSections) : ServiceCheckResult
    }

    abstract Fetcher {
        fetch() : RawData
    }
    abstract Parser {
        parse(RawData) : HostSections
    }
    abstract Summarizer {
        summarize(HostSections) : ServiceCheckResult
    }

    Source ..> Fetcher : delegates
    Source ..> Parser : delegates
    Source ..> Summarizer : delegates

See Also:
    cmk.core_helpers: Implementation of the core helpers.

"""

from . import agent, fetcher_configuration, ipmi, piggyback, programs, snmp, tcp
from ._abstract import *
from ._checkers import *
