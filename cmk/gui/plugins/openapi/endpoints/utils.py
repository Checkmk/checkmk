#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Any, Dict, Literal, Sequence

from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects import constructors

GroupName = Literal[
    'host_group_config',
    'contact_group_config',
    'service_group_config',
]  # yapf: disable


def serve_group(group, serializer):
    response = Response()
    response.set_data(json.dumps(serializer(group)))
    if response.status_code != 204:
        response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_dict(group).to_header())
    return response


def serialize_group_list(
    domain_type: GroupName,
    collection: Sequence[Dict[str, Any]],
) -> constructors.CollectionObject:
    return constructors.collection_object(
        domain_type=domain_type,
        value=[
            constructors.collection_item(
                domain_type=domain_type,
                obj={
                    'title': group['alias'],
                    'id': group['id'],
                },
            ) for group in collection
        ],
        links=[constructors.link_rel('self', constructors.collection_href(domain_type))],
    )


def serialize_group(name: GroupName) -> Any:
    def _serializer(group):
        # type: (Dict[str, str]) -> Any
        ident = group['id']
        return constructors.domain_object(
            domain_type=name,
            identifier=ident,
            title=group['alias'],
            members={
                'title': constructors.object_property(
                    name='title',
                    value=group['alias'],
                    prop_format='string',
                    base=constructors.object_href(name, ident),
                ),
            },
            extensions={},
        )

    return _serializer
