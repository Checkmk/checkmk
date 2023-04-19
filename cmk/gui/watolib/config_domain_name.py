#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

ConfigDomainName = str

CORE: Final[ConfigDomainName] = "check_mk"
GUI: Final[ConfigDomainName] = "multisite"
LIVEPROXY: Final[ConfigDomainName] = "liveproxyd"
EVENT_CONSOLE: Final[ConfigDomainName] = "ec"
CA_CERTIFICATES: Final[ConfigDomainName] = "ca-certificates"
OMD: Final[ConfigDomainName] = "omd"
