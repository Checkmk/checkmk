#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import hashlib
import json
from typing import (  # pylint: disable=unused-import
    Text, Dict, Tuple, Any, List, Literal, Optional, Union, Callable)

from connexion import ProblemException  # type: ignore[import]
from werkzeug.datastructures import ETags

from cmk.gui.globals import request
from cmk.gui.http import Response

LocationType = Optional[Union[Literal['path'], Literal['query'], Literal['header'],
                              Literal['cookie']]]
ResultType = Literal["object", "list", "scalar", "void"]
LinkType = Dict

# We need to have a registry to allow plugins from other contexts (cee, cme, etc.) to be linked to
# from here (raw). The key is the domain-type (folder, host, etc.) the values are link-factories
# which take a base-url.
DOMAIN_OBJECT_LINK_REGISTRY = collections.defaultdict(list)  # type: Dict[str, List[Callable]]


def _action(name):
    return '/actions/%s' % (name,)


def _invoke(name):
    return _action(name) + '/invoke'


RestfulLinkRel = Literal[
    ".../action",
    ".../action-param",
    ".../add-to;",
    ".../attachment;",
    ".../choice;",
    ".../clear",
    ".../collection",
    ".../default",
    ".../delete",
    ".../details;",
    ".../domain-type",
    ".../domain-types",
    ".../element",
    ".../element-type",
    ".../invoke",
    ".../modify",
    ".../persist",
    ".../property",
    ".../remove-from;",
    ".../return-type",
    ".../service;",
    ".../services",
    ".../update",
    ".../user",
    ".../value;",
    ".../version",
]  # yapf: disable


def link_rel(
    rel,  # type: Union[RestfulLinkRel, str]
    href,
    method='GET',
    content_type='application/json',
    profile=None,
):
    """Link to a separate entity

    TODO:
        This should be 2 functions, one for spec-compliant rel-types, and one for check-mk
        internal rel-types.

    Args:
        rel:
            The rel value.

        href:
            The destination HTTP URL

        method:
            The HTTP method to user for this URL

        content_type:
            The content-type that needs to be sent for this URL to return the desired result

        profile:
            Additional profile data to change the behaviour of the URL response.

    Returns:
        A dict representing the link

    """
    method = method.upper()
    if profile is not None:
        content_type += ";profile=" + profile

    return {
        'rel': expand_rel(rel),
        'href': href,
        'method': method,
        'type': content_type,
    }


def expand_rel(rel):
    """Expand abbreviations in the rel field

    `.../` and `cmk/` are shorthands for the restful-objects and CheckMK namespaces.
    """
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    elif rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")

    return rel


def require_etag(etag):
    # type: (ETags) -> None
    if request.if_match.as_set() != etag.as_set():
        raise ProblemException(
            412,
            "Precondition failed",
            "ETag didn't match. Probable cause: Object changed by another user.",
        )


def rel_name(rel, **kw):
    """Generate a relationship name including it's parameters.

    Notes:
        No checking is done for the validity of the parameters in relation to the
        rel-value name. Please consult the Spec 2.7.1.2 for detailed information about
        the allowed parameters.

    Examples:

        >>> rel_name('self')
        'self'

        >>> rel_name('.../update', action="move")
        '.../update;action="move"'

        >>> rel_name('.../update;', action="move")
        '.../update;action="move"'

    Args:
        rel:
            The rel-name.

        **kw:
            Additional parameters.

    Returns:
        The rel-name with it's parameters concatenated.

    """
    if len(kw) == 1:
        for key, value in kw.items():
            rel = rel.rstrip(";") + ';%s="%s"' % (key, value)
    return rel


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


def action_result(
    action_links,  # type: List[LinkType]
    result_type,  # type: ResultType
    result_links,  # type: List[LinkType]
    result_value,  # type: Optional[Any]
):
    # type: (...) -> Dict
    """Construct an Action Result resource

    Described in Restful Objects, chapter 19.1-4 """
    return {
        'links': action_links,
        'resultType': result_type,
        'result': {
            'links': result_links,
            'value': result_value,
        }
    }


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
    links = [
        link_rel('self', uri, method='GET'),
        link_rel('.../update', uri, method='PUT'),
        link_rel('.../delete', uri, method='DELETE'),
    ]
    for link_factory in DOMAIN_OBJECT_LINK_REGISTRY.get(domain_type, []):
        links.append(link_factory(uri))
    return {
        'domainType': domain_type,
        'title': title,
        'links': links,
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
    response = Response()
    response.set_content_type(content_type)
    response.set_data(json.dumps(data))
    # HACK: See wrap_with_validation.
    response.original_data = data  # type: ignore[attr-defined]
    return response


def action_parameter(action, parameter, friendly_name, optional, pattern):
    return (action, {
        'id': '%s-%s' % (action, parameter),
        'name': parameter,
        'friendlyName': friendly_name,
        'optional': optional,
        'pattern': pattern,
    })


def etag_of_dict(dict_):
    """Build a sha256 hash over a dictionary's content.

    Keys are sorted first to ensure a stable hash.

    Args:
        dict_ (dict): A dictionary.

    Returns:
        str: The hex-digest of the built hash.

    """
    _hash = hashlib.sha256()
    for key in sorted(dict_.keys()):
        _hash.update(dict_[key])
    return ETags(strong_etags=_hash.hexdigest())


def etag_of_obj(obj):
    """Build an ETag from an objects last updated time.

    Args:
        obj: An object with a `updated_at` method.

    Returns:
        The value which the method returns, else raises a `ProblemException`.

    """
    updated_at = obj.updated_at()
    assert updated_at is not None
    if updated_at is None:
        raise ProblemException(500, "Object %r has no meta_data." % (obj.name(),),
                               "Can't create ETag.")

    return ETags(strong_etags=[str(updated_at)])


def param(
    param_name,  # type: str
    description=None,  # type: Optional[str]
    location=None,  # type: LocationType
    required=True,  # type: bool
    allow_emtpy=False,  # type: bool
    schema_type='string',  # type: str
    schema_pattern=None,  # type: str
    **kw):
    # type: (...) -> Union[str, dict]
    """Specify an OpenAPI parameter to be used on a particular endpoint.

    Args:
        param_name:
            The name of the parameter.

        description:
            Optionally the description of the parameter. Markdown may be used.

        location:
            One of 'query', 'path', 'cookie', 'header'.

        required:
            If `location` is `path` this needs to be set and True. Otherwise it can even be absent.

        allow_emtpy:
            If None as a value is allowed.

        schema_type:
            May be 'string', 'bool', etc.

        schema_pattern:
            A regex which is used to filter invalid values.

    Returns:
        The parameter dict.

    """
    if location is None:
        return param_name

    if location == 'path' and not required:
        raise ValueError("path parameters' `required` field always needs to be True!")

    schema = {'type': schema_type}
    if schema_pattern is not None:
        schema['pattern'] = schema_pattern
    _param = {
        'name': param_name,
        'in': location,
        'required': required,
        'description': description,
        'allowEmptyValue': allow_emtpy,
        'schema': schema
    }
    for key, value in kw.items():
        if key in _param:
            raise ValueError("Please specify %s through the normal parameters." % key)
        _param[key] = value
    return _param
