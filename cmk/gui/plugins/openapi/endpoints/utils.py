#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import http.client

from typing import Any, Dict, Literal, Sequence, List, Optional, Type

from connexion import ProblemException  # type: ignore[import]

from cmk.gui.http import Response
from cmk.gui.groups import load_group_information, GroupSpecs, GroupSpec
from cmk.gui.plugins.openapi.livestatus_helpers.types import Column, Table
from cmk.gui.plugins.openapi.restful_objects import constructors
from cmk.gui.watolib.groups import edit_group, GroupType


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


def update_groups(group_type: GroupType, entries: List[Dict[str, Any]]):
    groups = []
    for details in entries:
        name = details['name']
        edit_group(name, group_type, details['attributes'])
        groups.append(name)

    return fetch_specific_groups(groups, group_type)


def _verify_groups_exist(group_type: str, entries: List[Dict[str, Any]]):
    specific_existing_groups = load_group_information()[group_type]
    missing_groups = []
    for details in entries:
        name = details['name']
        if name not in specific_existing_groups:
            missing_groups.append(name)

    if missing_groups:
        raise ProblemException(
            status=400,
            title=f"Some {group_type} groups do not exist",
            detail=f"The following {group_type} groups do not exist: {', '.join(missing_groups)}")


def verify_group_exist(group_type: str, name):
    specific_existing_groups = load_group_information()[group_type]
    return name in specific_existing_groups


def load_groups(group_type: str, entries: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    specific_existing_groups = load_group_information()[group_type]
    group_details = {}
    already_existing = []
    for details in entries:
        name = details['name']
        if name in specific_existing_groups:
            already_existing.append(name)
            continue
        group_details[name] = details.get('alias')

    if already_existing:
        raise ProblemException(
            status=400,
            title=f"Some {group_type} groups already exist",
            detail=
            f"The following {group_type} group names already exist: {', '.join(already_existing)}",
        )

    return group_details


def verify_columns(table: Type[Table], column_names: List[str]) -> List[Column]:
    """Check for any wrong column spellings on the Table classes"""
    missing = set(column_names) - set(table.__columns__())
    if missing:
        raise ProblemException(
            title="Some columns could not be recognized",
            detail=(f"The following columns are not known on the {table.__tablename__} table:"
                    f" {', '.join(missing)}"),
        )

    return [getattr(table, col) for col in column_names]


def add_if_missing(columns: List[str], mandatory=List[str]) -> List[str]:
    ret = columns[:]
    for required in mandatory:
        if required not in ret:
            ret.append(required)
    return ret


def fetch_group(
    ident: str,
    group_type: GroupType,
    status: int = 404,
    message: Optional[str] = None,
) -> GroupSpec:
    groups = load_group_information()[group_type]
    group = _retrieve_group(ident, groups, status, message)
    group['id'] = ident
    return group


def fetch_specific_groups(
    idents: List[str],
    group_type: GroupType,
    status: int = 404,
    message: Optional[str] = None,
) -> List[GroupSpec]:
    groups = load_group_information()[group_type]
    result = []
    for ident in idents:
        group = _retrieve_group(ident, groups, status, message)
        group['id'] = ident
        result.append(group)
    return result


def _retrieve_group(
    ident: str,
    groups: GroupSpecs,
    status: int,
    message: Optional[str],
) -> GroupSpec:
    try:
        group = groups[ident].copy()
    except KeyError as exc:
        if message is None:
            message = str(exc)
        raise ProblemException(status, http.client.responses[status], message)
    return group
