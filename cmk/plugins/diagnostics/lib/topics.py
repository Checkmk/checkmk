#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The topics of the built-in support diagnostics plugins

Topics group the plugins in the GUI; users choose one sensitivity threshold
per topic. Topics are compared by value, so plugins of other families may
reference these topics by declaring an equal Topic instance.
"""

from cmk.diagnostics.internal import Topic

TOPIC_GENERAL = Topic("General site information")
TOPIC_OPERATING_SYSTEM = Topic("Operating system & hardware")
TOPIC_PERFORMANCE = Topic("Performance & sizing")
TOPIC_EXTENSIONS = Topic("Local files & extensions")
TOPIC_CRASH_REPORTS = Topic("Crash reports")
TOPIC_CONFIGURATION = Topic("Configuration files")
TOPIC_LOGS = Topic("Log files")
TOPIC_MONITORING_CORE = Topic("Monitoring core & daemons")
TOPIC_LICENSING = Topic("Licensing")
TOPIC_BUSINESS_INTELLIGENCE = Topic("Business Intelligence")
