#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Site CN authorization logic for validating client certificates against local site CN."""

from fastapi import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from cmk.agent_receiver.lib.certs import get_local_site_cn
from cmk.agent_receiver.lib.log import logger


def validate_site_cn_authorization(client_cn: str) -> None:
    """Validate that the client certificate CN matches the local site's CN.

    This function performs authorization by comparing the client's certificate
    common name (CN) with the local site's CN. It's used to ensure that only
    requests with a certificate matching the site's own identity are accepted.

    Args:
        client_cn: The common name extracted from the client's certificate

    Raises:
        HTTPException: HTTP 403 if the client CN doesn't match the local site's CN
    """
    local_site_cn = get_local_site_cn()
    if client_cn != local_site_cn:
        logger.warning(
            f"Site CN authorization failed: Client CN '{client_cn}' does not match local site CN '{local_site_cn}'"
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Client certificate CN ({client_cn}) does not match local site CN ({local_site_cn})",
        )
