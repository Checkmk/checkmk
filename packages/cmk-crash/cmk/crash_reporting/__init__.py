#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Full crash-reporting library: packaging, payload construction, and (Epic 2) upload.

Skeleton in this epic. Depends on ``cmk.crash`` for the dataclasses
and store. The tar packaging helper and inline payload-construction block
currently inlined in ``cmk/gui/crash_reporting/pages.py`` land here later.
The batch upload loop and CLI entrypoint (``cmk-upload-crashes``) land in
Epic 2.
"""
