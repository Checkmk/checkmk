#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Ask this site's own REST API which agent updater its hosts run

Only an edition with the Agent Bakery can count this, and this module ships in every
edition under the GPL, so it may not import the bakery. It therefore asks the bakery's
internal endpoint over the site's own REST API instead of computing anything itself.
"""

from http import HTTPStatus
from logging import Logger
from pathlib import Path

import requests

from cmk.ccc.site import get_apache_port
from cmk.product_usage.schema import AgentUpdaterData
from cmk.utils.local_secrets import SiteInternalSecret

_ENDPOINT_PATH = "check_mk/api/internal/domain-types/agent/actions/updater_usage/invoke"

# The endpoint counts while answering, and it reads one deployment file per host with agent
# updates enabled. Measured at 0.4 s warm and 2.6 s cold for 10,000 such hosts, so this
# bounds a setup an order of magnitude larger. It is the timeout of 'transmission.py' too.
_TIMEOUT_SECONDS = 30


def collect(omd_root: Path, site_id: str, logger: Logger) -> AgentUpdaterData | None:
    """Report which agent updater the hosts of this site run

    Args:
        omd_root: The site directory, which holds the Apache port of this site.
        site_id: The name of this site, which is the first element of every site URL.
        logger: Where the reason for an answer of None is recorded.

    Returns:
        The counts, or None where this site does not answer them: an edition without the
        Agent Bakery, a remote site, or a release older than the endpoint. The payload
        then carries null, which means "not collected by this release".

    Raises:
        requests.RequestException: The site did not answer at all.
        pydantic.ValidationError: The site answered something other than the counts.
    """
    url = f"http://localhost:{get_apache_port(omd_root)}/{site_id}/{_ENDPOINT_PATH}"
    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"InternalToken {SiteInternalSecret().secret.b64_str}",
        },
        timeout=_TIMEOUT_SECONDS,
    )

    if response.status_code != HTTPStatus.OK:
        logger.info(
            "The site does not report the agent updater usage (HTTP %(status)d), sending none",
            {"status": response.status_code},
        )
        return None

    return AgentUpdaterData.model_validate_json(response.content)
