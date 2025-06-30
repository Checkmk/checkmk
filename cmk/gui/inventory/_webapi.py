#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal, TypedDict

from cmk.ccc.exceptions import MKException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId

from cmk.utils.structured_data import SDRawTree, serialize_tree

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _

from . import _xml
from ._tree import inventory_of_host, make_filter_choices_from_api_request_paths


def _check_for_valid_hostname(hostname: str) -> None:
    """test hostname for invalid chars, raises MKUserError if invalid chars are found
    >>> _check_for_valid_hostname("klappspaten")
    >>> _check_for_valid_hostname("../../etc/passwd")
    Traceback (most recent call last):
    cmk.gui.exceptions.MKUserError: You need to provide a valid "host name". Only letters, digits, dash, underscore and dot are allowed.
    """
    try:
        HostAddress(hostname)
    except ValueError:
        raise MKUserError(
            None,
            _(
                'You need to provide a valid "host name". '
                "Only letters, digits, dash, underscore and dot are allowed.",
            ),
        )


class _HostInvAPIResponse(TypedDict):
    result_code: Literal[0, 1]
    result: str | Mapping[str, SDRawTree]


def _write_json(resp):
    response.set_data(json.dumps(resp, sort_keys=True, indent=4, separators=(",", ": ")))


def _write_xml(resp):
    dom = _xml.dict_to_document(resp)
    response.set_data(dom.toprettyxml())


def _write_python(resp):
    response.set_data(repr(resp))


def page_host_inv_api(config: Config) -> None:
    resp: _HostInvAPIResponse
    try:
        api_request = request.get_request()
        if not (hosts := api_request.get("hosts")):
            if (host_name := api_request.get("host")) is None:
                raise MKUserError("host", _('You need to provide a "host".'))
            hosts = [host_name]

        result: dict[str, SDRawTree] = {}
        for raw_host_name in hosts:
            _check_for_valid_hostname(raw_host_name)
            result[raw_host_name] = serialize_tree(
                inventory_of_host(
                    SiteId(raw_site_id) if (raw_site_id := api_request.get("site")) else None,
                    HostName(raw_host_name),
                    (
                        make_filter_choices_from_api_request_paths(api_request["paths"])
                        if "paths" in api_request
                        else []
                    ),
                )
            )

        resp = {"result_code": 0, "result": result}

    except MKException as e:
        resp = {"result_code": 1, "result": "%s" % e}

    except Exception as e:
        if config.debug:
            raise
        resp = {"result_code": 1, "result": "%s" % e}

    if html.output_format == "json":
        _write_json(resp)
    elif html.output_format == "xml":
        _write_xml(resp)
    else:
        _write_python(resp)
