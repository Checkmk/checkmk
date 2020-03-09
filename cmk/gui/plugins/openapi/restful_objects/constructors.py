#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import typing

if typing.TYPE_CHECKING:
    from typing import Text, Dict, Tuple, Any, List  # pylint: disable=unused-import
    from werkzeug.datastructures import ETags  # pylint: disable=unused-import

from connexion import ProblemException  # type: ignore[import]

from cmk.gui.globals import request, response


def _action(name):
    return '/actions/%s' % (name,)


def _invoke(name):
    return _action(name) + '/invoke'


def link_rel(rel, href, method='GET', content_type='application/json', profile=None):
    method = method.upper()
    if profile is not None:
        content_type += ";profile=" + profile

    return {
        'rel': rel,
        'href': href,
        'method': method,
        'type': content_type,
    }


def require_etag(etag):
    # type: (ETags) -> None
    if request.if_match.as_set() != etag.as_set():
        raise ProblemException(
            412,
            "Precondition failed",
            "ETag didn't match. Probable cause: Object changed by another user.",
        )


def rel_name(param, **kw):
    """Generate a relationship name.

    Examples:

        >>> rel_name('self')
        'self'

        >>> rel_name('.../update', action="move")
        '.../update;action="move"'

    Args:
        param:
        **kw:

    Returns:

    """
    if len(kw) == 1:
        for key, value in kw.items():
            param += ';%s="%s"' % (key, value)
    return param


def object_action_member(name, base, parameters):
    # type: (str, str, dict) -> Tuple[str, Dict[str, Any]]
    return (
        name,
        {
            'id': name,
            'memberType': "action",
            'links': [
                link_rel('up', base),
                link_rel(rel_name('.../details', action=name), base + _action(name)),
                link_rel(rel_name('.../invoke', action=name), base + _invoke(name), method='POST'),
                #               arguments={'destination': 'root'},
            ],
            #       'parameters': parameters,
        })


def object_collection_member(name, base, entries):
    # type: (str, str, List[str]) -> Tuple[str, Dict[str, Any]]
    return (name, {
        'id': name,
        'memberType': "collection",
        'value': entries,
        'links': [
            link_rel('self', base + "/collections/%s" % (name,)),
            link_rel('up', base),
        ]
    })


def object_property_member(name, value, base):
    # type: (str, str, str) -> Tuple[str, Dict[str, Any]]
    return (name, {
        'id': name,
        'memberType': "property",
        'value': value,
        'links': [link_rel('self', base + '/properties/' + name, profile='".../object_property"')],
        'choices': [],
    })


def object_href(domain_type, obj):
    # type: (str, Any) -> str
    return '/objects/%s/%s' % (
        domain_type,
        obj.id(),
    )


def domain_object(domain_type, identifier, title, members, extensions):
    uri = "/objects/%s/%s" % (domain_type, identifier)
    return {
        'domainType': domain_type,
        'title': title,
        'links': [
            link_rel('self', uri, method='GET'),
            link_rel('.../update', uri, method='PUT'),
            link_rel('.../delete', uri, method='DELETE'),
        ],
        'members': members,
        'extensions': extensions,
    }


def collection_object(collection_type, domain_type, obj):
    # type: (str, str, Any) -> Dict[str, Text]
    """A collection object as specified in C-115 (Page 121)

    Notes:
        This does not implement all of the spec.

    Args:
        collection_type:
        domain_type:
        obj:

    Returns:
        A dict representation of the collection object.

    """
    return {
        'rel': '.../value;collection="%s"' % (collection_type,),
        'href': object_href(domain_type, obj),
        'type': 'application/json;profile=".../object"',
        'method': 'GET',
        'title': obj.title(),
    }


def serve_json(data, profile=None):
    content_type = 'application/json'
    if profile is not None:
        content_type += ';profile="%s"' % (profile,)
    response.set_content_type(content_type)
    response.set_data(json.dumps(data))
    response.original_data = data
    return response._get_current_object()


def action_parameter(action, parameter, friendly_name, optional, pattern):
    return (action, {
        'id': '%s-%s' % (action, parameter),
        'name': parameter,
        'friendlyName': friendly_name,
        'optional': optional,
        'pattern': pattern,
    })


def sucess(status=200):
    response.status_code = status
    return response._get_current_object()
