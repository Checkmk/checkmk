#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.base_app import CheckmkBaseApp
from cmk.base.core.nagios.factory import create_core
from cmk.ccc.version import Edition
from cmk.fetchers import PlainFetcherTrigger
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.utils.labels import get_builtin_host_labels
from cmk.utils.paths import omd_root


def make_app() -> CheckmkBaseApp:
    return CheckmkBaseApp(
        edition=Edition.COMMUNITY,
        make_bake_on_restart=lambda *args: lambda: None,
        create_core=create_core,
        licensing_handler_factory=CommunityLicensingHandler.make,
        make_fetcher_trigger=lambda *a, **kw: PlainFetcherTrigger(omd_root=omd_root),
        make_metric_backend_fetcher=lambda *args: None,
        get_builtin_host_labels=get_builtin_host_labels,
        core_performance_settings=lambda _: {},
    )
