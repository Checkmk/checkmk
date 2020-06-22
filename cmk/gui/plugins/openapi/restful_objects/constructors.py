#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
import json
from typing import Any, Dict, List, Optional, Union

from connexion import ProblemException  # type: ignore[import]
from werkzeug.datastructures import ETags

from cmk.gui.globals import request
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    CollectionItem,
    CollectionObject,
    DomainObject,
    DomainType,
    EndpointName,
    HTTPMethod,
    LinkType,
    PropertyFormat,
    RestfulEndpointName,
    ResultType,
    Serializable,
)
from cmk.gui.plugins.openapi.restful_objects.utils import (
    fill_out_path_template,
    ENDPOINT_REGISTRY,
)


def link_rel(
        rel,  # type: Union[RestfulEndpointName, EndpointName]
        href,  # type: str
        method='get',  # type: HTTPMethod
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
        ...                 method='get', profile='.../object', title='Update the object')
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
            link_rel('.../invoke', base + _invoke(name), method='post',
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
        link_rel('self', uri, method='get'),
    ]
    if editable:
        _links.append(link_rel('.../update', uri, method='put'))
    if deletable:
        _links.append(link_rel('.../delete', uri, method='delete'))
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


def link_endpoint(
    module_name,
    rel: Union[EndpointName, RestfulEndpointName],
    parameters: Dict[str, str],
    _registry=ENDPOINT_REGISTRY,
):
    """Link to a specific endpoint by name.

    Args:
        module_name:
            The Python dotted path name, where the endpoint to be linked to, is defined.

        rel:
            The endpoint's rel-name.

        parameters:
            A dict, mapping parameter names to their desired values. e.g. if the link should have
            "/foo/{baz}" rendered to "/foo/bar", this mapping should be {'baz': 'bar'}.

        _registry:
            Internal use only.

    Examples:

        >>> from cmk.gui.plugins.openapi.restful_objects.utils import make_endpoint_entry
        >>> registry = {
        ...     ('roll', '.../invoke'): make_endpoint_entry(
        ...          'post',
        ...          '/random/{dice_roll_result}',
        ...          [],  # not needed for this example
        ...     ),
        ... }
        >>> expected = {
        ...     'rel': 'urn:org.restfulobjects:rels/invoke',
        ...     'href': '/random/4',
        ...     'method': 'POST',
        ...     'type': 'application/json',
        ...     'domainType': 'link',
        ... }
        >>> link = link_endpoint(
        ...     'roll',
        ...     '.../invoke',
        ...     parameters={'dice_roll_result': "4"},
        ...     _registry=registry,  # for doctest, not be used
        ... )
        >>> assert link == expected, link

    """
    try:
        endpoint = _registry[(module_name, rel)]
    except KeyError:
        raise KeyError(_registry.keys())

    param_values = {key: {'example': value} for key, value in parameters.items()}

    return link_rel(
        rel=rel,
        href=fill_out_path_template(endpoint['path'], param_values),
        method=endpoint['method'],
        # This one needs more work to get the structure right.
        # parameters=endpoint['parameters']
    )


def collection_item(collection_type, domain_type, obj):
    # type: (str, DomainType, Any) -> CollectionItem
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
        method='get',
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
