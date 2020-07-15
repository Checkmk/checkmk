#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any as _Any, Dict as _Dict, List as _List, Union as _Union

import cmk.utils.version as cmk_version

# Log level of notifications
# 0, 1, 2 -> deprecated (transformed to 20, 20, and 10)
# 20 -> minimal logging
# 15 -> normal logging
# 10 -> full dump of all variables and command
notification_logging = 15
notification_backlog = 10  # keep the last 10 notification contexts for reference

# Settings for new rule based notifications
enable_rulebased_notifications = False
notification_fallback_email = ""
notification_rules: _List[_Dict[str, _Any]] = []
# Check every 10 seconds for ripe bulks
notification_bulk_interval = 10
notification_plugin_timeout = 60

# Notification Spooling.

# Possible values for notification_spooling
# "off"    - Direct local delivery without spooling
# "local"  - Asynchronous local delivery by notification spooler
# "remote" - Forward to remote site by notification spooler
# "both"   - Asynchronous local delivery plus remote forwarding
# False    - legacy: sync delivery  (and notification_spool_to)
# True     - legacy: async delivery (and notification_spool_to)
if cmk_version.is_raw_edition():
    notification_spooling: _Union[bool, str] = "off"
else:
    notification_spooling = "local"

# Legacy setting. The spool target is now specified in the
# configuration of the spooler. notification_spool_to has
# the tuple format (remote_host, tcp_port, also_local)
notification_spool_to = None
