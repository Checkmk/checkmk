#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
import json
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict

from connexion import ProblemException  # type: ignore[import]
from werkzeug.datastructures import ETags

from cmk.gui.globals import request
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects.type_defs import (EndpointName, HTTPMethod,
                                                               RestfulEndpointName, PropertyFormat,
                                                               DomainType, DomainObject)
from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict

LinkType = Dict[str, str]
CollectionItem = Dict[str, str]
CollectionObject = TypedDict('CollectionObject', {
    'id': str,
    'domainType': str,
    'links': List[LinkType],
    'value': Any,
    'extensions': Dict[str, str]
})
Serializable = Union[Dict[str, Any], CollectionObject]  # because TypedDict is stricter
LocationType = Optional[Literal['path', 'query', 'header', 'cookie']]
ResultType = Literal["object", "list", "scalar", "void"]


def link_rel(
        rel,  # type: Union[RestfulEndpointName, EndpointName]
        href,  # type: str
        method='GET',  # type: HTTPMethod
        content_type='application/json',  # type: str
        profile=None,  # type: Optional[str]
        title=None,  # type: Optional[str]
        parameters=None,  # type: Optional[Dict[str, str]]
):
    # type: (...) -> LinkType
    """Link to a separate entity

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
            (Optional) Additional profile data to change the behaviour of the URL response.

        title:
            (Optional) A pretty printed string for UIs to render.

        parameters:
            (Optional) Parameters for the rel-value. e.g. rel='foo', parameters={'baz': 'bar'}
            will result in a rel-value of 'foo;baz="bar"'

    Examples:

        >>> link = link_rel('.../update', 'update',
        ...                 method='GET', profile='.../object', title='Update the object')
        >>> expected = {
        ...     'domainType': 'link',
        ...     'type': 'application/json;profile="urn:org.restfulobjects:rels/object"',
        ...     'method': 'GET',
        ...     'rel': 'urn:org.restfulobjects:rels/update',
        ...     'title': 'Update the object',
        ...     'href': 'update'
        ... }
        >>> assert link == expected, link

    Returns:
        A dict representing the link

    """
    content_type_params = {}
    if profile is not None:
        content_type_params['profile'] = expand_rel(profile)

    link_obj = {
        'rel': expand_rel(rel, parameters),
        'href': href,
        'method': method.upper(),
        'type': expand_rel(content_type, content_type_params),
        'domainType': 'link',
    }
    if title is not None:
        link_obj['title'] = title
    return link_obj


def expand_rel(
        rel,  # type: str
        parameters=None,  # type: Optional[Dict[str, str]]
):
    # type: (...) -> str
    """Expand abbreviations in the rel field

    `.../` and `cmk/` are shorthands for the restful-objects and CheckMK namespaces. The
    restful-objects one is required by the spec.

    Args:
        rel: The rel-value.

        parameters: A dict of additional parameters to be appended to the rel-value.

    Examples:

        >>> expand_rel('.../value', {'collection': 'items'})
        'urn:org.restfulobjects:rels/value;collection="items"'

        >>> expand_rel('cmk/launch', {'payload': 'coffee', 'count': 5})
        'urn:com.checkmk:rels/launch;count="5";payload="coffee"'

    """
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/")
    elif rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/")

    if parameters:
        for param_name, value in sorted(parameters.items()):
            rel += ';%s="%s"' % (param_name, value)

    return rel


def require_etag(etag):
    # type: (ETags) -> None
    """Ensure the current request matches the given ETag.

    Args:
        etag: An Werkzeug ETag instance to compare the global request instance to.

    Raises:
        ProblemException: When ETag doesn't match.
    """
    if request.if_match.as_set() != etag.as_set():
        raise ProblemException(
            412,
            "Precondition failed",
            "ETag didn't match. Probable cause: Object changed by another user.",
        )


def object_action(name, parameters, base):
    # type: (str, dict, str) -> Dict[str, Any]
    """A action description to be used as an object member.

    Examples:

        >>> action = object_action('move', {'from': 'to'}, '')
        >>> assert len(action['links']) > 0

    Args:
        name:
        parameters:
        base:

    Returns:

    """
    def _action(_name):
        return '/actions/%s' % (_name,)

    def _invoke(_name):
        return _action(_name) + '/invoke'

    return {
        'id': name,
        'memberType': "action",
        'links': [
            link_rel('up', base),
            link_rel('.../details', base + _action(name), parameters={'action': name}),
            link_rel('.../invoke', base + _invoke(name), method='POST',
                     parameters={'action': name}),
        ],
        'parameters': parameters,
    }


def object_collection(name, entries, base):
    # type: (str, List[Union[LinkType, DomainObject]], str) -> Dict[str, Any]
    """A collection description to be used as an object member.

    Args:
        name:
        entries:
        base:

    Returns:

    """
    return {
        'id': name,
        'memberType': "collection",
        'value': entries,
        'links': [
            link_rel('self', base + "/collections/%s" % (name,)),
            link_rel('up', base),
        ]
    }


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


def object_property(
        name,  # type: str
        value,  # type: Any
        prop_format,  # type: PropertyFormat
        base,  # type: str
        title=None,  # type: Optional[str]
        linkable=True,  # type: bool
        links=None,  # type: Optional[List[LinkType]]
):
    # type: (...) -> Dict[str, Any]
    """Render an object-property

    Args:
        name:
            The name of the property.

        value:
            The value of the property. Needs to conform the the selected prop_format type. No
            validation is done though.

        prop_format:
            The formal name of the property's type.

        base:
            The base-url which to prefix all generated links.

        title:
            (Optional) A pretty-printed string which a UI can use to render.

        linkable:
            If this property has it's own URL to be queried directly. Defaults to True.

        links:
            (Optional) Additional links to be appended to the list.

    Returns:
        A dictionary representing an object-property.

    """
    property_obj = {
        'id': name,
        'memberType': "property",
        'value': value,
        'format': prop_format,
        'title': title,
        'choices': [],
    }
    if linkable:
        property_obj['links'] = [
            link_rel('self', base + '/properties/' + name, profile='.../object_property')
        ]
        if links:
            property_obj['links'].extend(links)

    return property_obj


def object_href(domain_type, obj):
    # type: (str, Any) -> str
    """

    Args:
        domain_type:
        obj:

    Examples:

        >>> object_href('folder', {'title': 'Main', 'id': 0})
        '/objects/folder/0'

    Returns:

    """
    _id = getattr(obj, 'id', None)
    if callable(_id):
        obj_id = _id()
    else:
        obj_id = obj['id']

    return '/objects/{domain_type}/{obj_id}'.format(
        domain_type=domain_type,
        obj_id=obj_id,
    )


def domain_object(
        domain_type,  # type: DomainType
        identifier,  # type: str
        title,  # type: str
        members=None,  # type: Optional[Dict[str, Any]]
        extensions=None,  # type: Optional[Dict[str, Any]]
        editable=True,  # type: bool
        deletable=True,  # type: bool
        links=None,  # type: Optional[List[LinkType]]
):
    # type: (...) -> DomainObject
    """Renders a domain-object dict structure.

    Most of the parameters are optional, yet without them nothing interesting would happen.

    Args:
        domain_type:
            The type of the object (e.g. folder, host, etc.)

        identifier:
            The "primary key" of the object. e.g. the hostname or something else.

        title:
            Something for a user-interface to display. Should be nice to read.

        members:
            (optional) A dictionary of keys to "members". May be `object_collection`,
            `object_property` or `object_action`.

        extensions:
            (optional) Additional information like metadata, or other data, not explicitly
            specified to be part of `members`.

        editable:
            If set, a link to the update-endpoint of this object will be added. Defaults to True.

        deletable:
            If set, a link to the delete-endpoint of this object will be added. Defaults to True.

        links:
            (optional) A list of `link_rel` dicts.

        """
    uri = "/objects/%s/%s" % (domain_type, identifier)
    if extensions is None:
        extensions = {}
    if members is None:
        members = {}
    _links = [
        link_rel('self', uri, method='GET'),
    ]
    if editable:
        _links.append(link_rel('.../update', uri, method='PUT'))
    if deletable:
        _links.append(link_rel('.../delete', uri, method='DELETE'))
    if links:
        _links.extend(links)
    return {
        'domainType': domain_type,
        'id': identifier,
        'title': title,
        'links': _links,
        'members': members,
        'extensions': extensions,
    }


def collection_object(domain_type: str,
                      value: List[Union[CollectionItem, LinkType]],
                      links: Optional[List[LinkType]] = None,
                      extensions: Any = None) -> CollectionObject:
    """A collection object as specified in C-115 (Page 121)

    Args:
        domain_type:
        value:
        links:
        extensions:

    Returns:

    """
    if extensions is None:
        extensions = {}
    _links = [
        link_rel('self', "/collections/%s" % (domain_type,)),
    ]
    if links is not None:
        _links.extend(links)
    return {
        'id': domain_type,
        'domainType': domain_type,
        'links': _links,
        'value': value,
        'extensions': extensions,
    }


def collection_item(collection_type, domain_type, obj):
    # type: (str, str, Any) -> CollectionItem
    """A link for use in a collection object.

    Args:
        collection_type:
        domain_type:
        obj:

    Examples:

        >>> expected = {
        ...     'domainType': 'link',
        ...     'href': '/objects/folder/3',
        ...     'method': 'GET',
        ...     'rel': 'urn:org.restfulobjects:rels/value;collection="folder"',
        ...     'title': 'Foo',
        ...     'domainType': 'link',
        ...     'type': 'application/json;profile="urn:org.restfulobjects:rels/object"',
        ... }
        >>> res = collection_item('folder', 'folder', {'title': 'Foo', 'id': '3'})
        >>> assert res == expected, res

    Returns:
        A dict representation of the collection link-entry.

    """
    return link_rel(
        rel='.../value',
        parameters={'collection': collection_type},
        href=object_href(domain_type, obj),
        profile=".../object",
        method='GET',
        title=obj_title(obj),
    )


def obj_title(obj):
    _title = getattr(obj, 'title', None)
    if callable(_title):
        return _title()
    return obj['title']


def serve_json(data, profile=None):
    # type: (Serializable, Dict[str, str]) -> Response
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


def etag_of_dict(dict_) -> ETags:
    """Build a sha256 hash over a dictionary's content.

    Keys are sorted first to ensure a stable hash.

    Examples:
        >>> etag_of_dict({'a': 'b', 'c': 'd'})
        <ETags '"88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589"'>

    Args:
        dict_ (dict): A dictionary.

    Returns:
        str: The hex-digest of the built hash.

    """
    _hash = hashlib.sha256()
    for key in sorted(dict_.keys()):
        _hash.update(key.encode('utf-8'))
        _hash.update(dict_[key].encode('utf-8'))
    return ETags(strong_etags=[_hash.hexdigest()])


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
    # type: (...) -> ParamDict
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
    if location == 'path' and not required:
        raise ValueError("path parameters' `required` field always needs to be True!")

    schema = {'type': schema_type}
    if schema_pattern is not None:
        schema['pattern'] = schema_pattern
    _param = ParamDict({
        'name': param_name,
        'in': location,
        'required': required,
        'description': description,
        'allowEmptyValue': allow_emtpy,
        'schema': schema
    })
    for key, value in kw.items():
        if key in _param:
            raise ValueError("Please specify %s through the normal parameters." % key)
        _param[key] = value
    return _param
