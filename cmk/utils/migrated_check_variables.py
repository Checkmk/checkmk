#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This file was originally created to collect variables that have been needed to load
the autochecks file, as it could contain *references* to those variables.
As of 2.0, we no longer store those references, and we resolve them during update-config.

However, I don't dare to delete this file completely, as it influences the way the variables
are treated during the magical context manipulations in cmk.base.config.

Removing variables from this file may probably render some configurations invalid.
I think.
"""

# if.include
# These HostRulespecs are deprecated as of v2.0. However, for compatibility reasons, we must not
# delete these variable.
if_disable_if64_hosts: list = []
if_groups: list = []
