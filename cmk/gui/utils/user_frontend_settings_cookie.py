#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.parse
from dataclasses import asdict

from cmk.ccc.site import url_prefix
from cmk.gui.http import Request, Response
from cmk.shared_typing.user_frontend_config import UserFrontendConfig


def del_user_frontend_config_cookie(response: Response) -> None:
    response.delete_cookie("user_frontend_config", path=url_prefix())


def set_user_frontend_config_cookie(
    request: Request, response: Response, conf: UserFrontendConfig
) -> None:
    # Cookies need to be encoded, things like commas are not allowed etc.
    data = urllib.parse.quote(json.dumps({k: v for k, v in asdict(conf).items() if v is not None}))
    response.set_cookie("user_frontend_config", data, path=url_prefix(), secure=request.is_secure)
