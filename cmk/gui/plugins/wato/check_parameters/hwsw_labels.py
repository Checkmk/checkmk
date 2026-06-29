#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Hardware/Software Inventory Label Creator for Checkmk Discovery

INTENTION
=========
This module provides WATO UI configuration for automatically generating host labels
from the Checkmk Hardware/Software (hwsw) inventory. The hwsw inventory contains
detailed information about:

- Hardware components (CPU, memory, disks, network interfaces, etc.)
- Software installed (packages, services, configurations, etc.)
- System characteristics (vendor, model, serial number, BIOS version, etc.)

By configuring label creation rules in WATO, administrators can:

1. Extract inventory data using path-based selectors on the hwsw tree structure
2. Transform extracted data into human-readable host labels
3. Use these labels for grouping, filtering, and organizing hosts in Checkmk

"""

# This is a placeholder file that documents the intended functionality.
# The actual implementation will follow when the feature is developed.
# See examples above for the vision of how hwsw inventory data will be
# transformed into useful host labels for Checkmk monitoring.
