#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Resolve the customer a monitored host belongs to."""

from collections.abc import Callable

from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.livestatus_client import SiteConfigurations


def customer_resolver(*, sites: SiteConfigurations) -> Callable[[str], str | None]:
    """Look up the name of the customer a host is monitored for.

    Multi-tenancy assigns a customer to a site, and Setup only lets a host live on a site of
    its own customer, so the two are the same thing. Deriving it from the site configuration
    keeps it in step with Setup; the `_CUSTOMER` custom variable Livestatus serves is a
    snapshot the monitoring core only rewrites when the site activates its core configuration.

    Editions without multi-tenancy know no customers at all, which their customer API reports
    as the global scope, so every host comes back without one.

    Returns a lookup rather than answering directly because a whole page of hosts is resolved
    at once, while which of the two sources applies is settled once per request.
    """
    api = customer_api()

    def name_of(customer_id: str | None) -> str | None:
        # Asked for a customer that isn't one, the stub would answer with the string "None".
        return None if customer_id is None else api.get_customer_name_by_id(customer_id)

    if is_distributed_setup_remote_site(sites):
        # A remote site is told its own customer, but never the site list to look one up in,
        # and every host it monitors is that one customer's. Read straight from the loaded
        # configuration: the customer API resolves names out of it either way, and threading
        # the value through the shared API config would couple this page to that framework.
        name = name_of(active_config.raw.get("current_customer"))
        return lambda _site_id: name

    return lambda site_id: name_of(api.get_customer_id(sites.get(SiteId(site_id), {})))
