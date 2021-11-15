#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1 import equals, startswith

DETECT_FORTISANDBOX = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.118.1.30006")
DETECT_FORTIAUTHENTICATOR = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10")
DETECT_FORTIGATE = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1.")
DETECT_FORTIMAIL = equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.105")
