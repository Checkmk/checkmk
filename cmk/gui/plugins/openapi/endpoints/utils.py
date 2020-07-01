#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Any, Dict, Union, Literal

from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import constructors

GroupName = Union[Literal['host_group'], Literal['contact_group'], Literal['service_group'],]


def serve_group(group, serializer):
    response = Response()
    response.set_data(json.dumps(serializer(group)))
    if response.status_code != 204:
        response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_dict(group).to_header())
    return response


def serialize_group(name: GroupName) -> Any:
    def _serializer(group: Dict[str, str]) -> Any:
        ident = group['id']
        uri = '/object/%s/%s' % (
            name,
            ident,
        )
        return constructors.domain_object(
            domain_type=name,
            identifier=ident,
            title=group['alias'],
            members={
                'title': constructors.object_property(
                    name='title',
                    value=group['alias'],
                    prop_format='string',
                    base=uri,
                ),
            },
            extensions={},
        )

    return _serializer
