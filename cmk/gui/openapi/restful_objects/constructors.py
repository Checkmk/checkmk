#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import re
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, NewType
from urllib.parse import quote

from werkzeug.datastructures import ETags

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.http import HTTPMethod, request, Response
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from cmk.gui.openapi.restful_objects.type_defs import (
    ActionObject,
    ActionResult,
    CollectionItem,
    CollectionObject,
    DomainObject,
    DomainType,
    LinkRelation,
    LinkType,
    ObjectProperty,
    PropertyFormat,
    ResultType,
)
from cmk.gui.openapi.utils import EXT, ProblemException

ETagHash = NewType("ETagHash", str)


def absolute_url(href: str) -> str:
    if href.startswith("/"):
        href = href.lstrip("/")

    return f"{request.host_url}{omd_site()}/check_mk/api/1.0/{href}"


def link_rel(
    rel: LinkRelation,
    href: str,
    method: HTTPMethod = "get",
    content_type: str = "application/json",
    profile: str | None = None,
    title: str | None = None,
    parameters: dict[str, str] | None = None,
    body_params: dict[str, str | None] | None = None,
) -> LinkType:
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

        body_params:
            (Optional) A dict of values which shall be sent as body paramaters.

        parameters:
            (Optional) Parameters for the rel-value. e.g. rel='foo', parameters={'baz': 'bar'}
            will result in a rel-value of 'foo;baz="bar"'

    Returns:
        A LinkType

    """
    content_type_params = {}
    if profile is not None:
        content_type_params["profile"] = expand_rel(profile)

    link_obj: LinkType = {
        "rel": expand_rel(rel, parameters),
        "href": absolute_url(href),
        "method": method.upper(),
        "type": expand_rel(content_type, content_type_params),
        "domainType": "link",
    }
    if body_params is not None:
        link_obj["body_params"] = body_params
    if title is not None:
        link_obj["title"] = title
    return link_obj


def expand_rel(
    rel: str,
    parameters: dict[str, str] | None = None,
) -> str:
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

        >>> expand_rel('cmk/cmk/foo')
        'urn:com.checkmk:rels/cmk/foo'

    """
    if rel.startswith(".../"):
        rel = rel.replace(".../", "urn:org.restfulobjects:rels/", 1)
    elif rel.startswith("cmk/"):
        rel = rel.replace("cmk/", "urn:com.checkmk:rels/", 1)

    if parameters:
        for param_name, value in sorted(parameters.items()):
            rel += f';{param_name}="{value}"'

    return rel


def require_etag(
    etag: ETagHash,
    error_details: EXT | None = None,
) -> None:
    """Ensure current request 'If-Match' header matches the expected ETag or is a *


    Args:
        etag: An Werkzeug ETag instance to compare the global request instance to.

        error_details:
            An optional dict, which will be communicated to the client whenever there is an
            etag mismatch.

    Raises:
        ProblemException: When If-Match missing or ETag doesn't match.
    """
    if not active_config.rest_api_etag_locking:
        return

    if not request.if_match:
        raise ProblemException(
            HTTPStatus.PRECONDITION_REQUIRED,
            "Precondition required",
            "If-Match header required for this operation. See documentation.",
            ext=error_details,
        )

    if request.if_match.contains(etag):
        return

    raise ProblemException(
        HTTPStatus.PRECONDITION_FAILED,
        "Precondition failed",
        f"ETag didn't match. Expected {etag}. Probable cause: Object changed by another user.",
        ext=error_details,
    )


def object_action(name: str, parameters: dict, base: str) -> ActionObject:
    """An action description to be used as an object member"""

    return {
        "id": name,
        "memberType": "action",
        "links": [
            link_rel("up", base),
            link_rel(
                ".../invoke",
                base + f"/actions/{name}/invoke",
                method="post",
                parameters={"action": name},
            ),
        ],
        "parameters": parameters,
    }


def object_collection(
    name: str,
    domain_type: DomainType,
    entries: list[LinkType | DomainObject],
    base: str,
) -> dict[str, Any]:
    """A collection description to be used as an object member.

    Args:
        name:
            The name of the collection.

        domain_type:
            The domain-type the collection is a part of.

        entries:
            The entries in that collection.

        base:
            The base-level URI. May be an object's URI for example

    Returns:
        The object_collection structure.

    """
    links = [
        link_rel("self", base + collection_href(domain_type)),
    ]
    if base:
        links.append(link_rel("up", base))
    return {
        "id": name,
        "memberType": "collection",
        "value": entries,
        "links": links,
    }


def action_result(
    action_links: list[LinkType],
    result_type: ResultType,
    result_value: Any | None = None,
    result_links: list[LinkType] | None = None,
) -> ActionResult:
    """Construct an Action Result resource

    Described in Restful Objects, chapter 19.1-4"""
    if result_links is None:
        result_links = []
    return {
        "links": action_links,
        "resultType": result_type,
        "result": {
            "links": result_links,
            "value": result_value,
        },
    }


def object_property_href(
    domain_type: DomainType,
    identifier: str,
    property_name: str,
) -> str:
    return f"/objects/{domain_type}/{identifier}/properties/{property_name}"


def object_sub_property(
    domain_type: DomainType,
    ident: str,
    name: str,
    value: Any,
    disabled_reason: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> ObjectProperty:
    if extensions is None:
        extensions = {}
    ret: ObjectProperty = {
        "id": f"{ident}_{name}",
        "value": value,
        "extensions": extensions,
    }
    if disabled_reason is not None:
        ret["disabledReason"] = disabled_reason

    ret["links"] = [
        link_rel(
            rel=".../modify",
            href=object_property_href(domain_type, ident, name),
            method="put",
        ),
    ]

    return ret


def collection_property(
    name: str,
    value: list[Any],
    base: str,
) -> dict[str, str | list | list[LinkType]]:
    """Represent a collection property.

    This is a property on an object which hols a collection. This has to be stored in the "member"
    section of the object.

    Args:
        name:
            The name of the collection.
        value:
            The value of the collection, i.e. all the entries.

        base:
            The base url, i.e. the URL under which the collection is located.
    """
    return {
        "id": name,
        "memberType": "collection",
        "value": value,
        "links": [link_rel(rel="self", href=base.rstrip("/") + f"/collections/{name}")],
    }


def object_property(
    name: str,
    value: Any,
    prop_format: PropertyFormat,
    base: str,
    title: str | None = None,
    linkable: bool = True,
    links: list[LinkType] | None = None,
    extensions: dict[str, Any] | None = None,
    choices: list[Any] | None = None,
) -> dict[str, Any]:
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

        extensions:
            (Optional) Additional keywords which will be presented under the 'extensions' key.

        choices:
            (Optional) A list of informational values which can be used for 'value'.

    Returns:
        A dictionary representing an object-property.

    """
    property_obj = {
        "id": name,
        "memberType": "property",
        "value": value,
        "format": prop_format,
        "title": title,
    }
    if choices is not None:
        property_obj["choices"] = choices

    if linkable:
        property_obj["links"] = [link_rel("self", f"{base}/properties/{name}")]

    if links:
        property_obj.setdefault("links", [])
        property_obj["links"].extend(links)

    if extensions:
        property_obj["extensions"] = extensions

    return property_obj


def domain_type_action_href(domain_type: DomainType, action: str) -> str:
    """Constructs a href to a domain-type action.

    Args:
        domain_type:
            The domain-type, the action is part of.

        action:
            The action-name.

    Examples:
        >>> domain_type_action_href('activation_run', 'activate-changes')
        '/domain-types/activation_run/actions/activate-changes/invoke'

    Returns:
        The href.

    """
    return f"/domain-types/{domain_type}/actions/{action}/invoke"


def domain_object_collection_href(
    domain_type: DomainType,
    obj_id: str,
    collection_name: str,
) -> str:
    """Construct a href for a collection specific to a domain-object.

    Args:
        domain_type:
            The domain-type.

        obj_id:
            The domain-object's object-id.

        collection_name:
            The name of the collection.

    Examples:
        >>> domain_object_collection_href('folder_config', 'stuff', 'hosts')
        '/objects/folder_config/stuff/collections/hosts'

    Returns:
        The href as a string.

    """
    return f"/objects/{domain_type}/{url_safe(obj_id)}/collections/{collection_name}"


def sub_object_href(
    domain_type: DomainType,
    obj_id: str,
    parent_domain_type: DomainType,
    parent_id: str,
) -> str:
    """Constructs a href to a sub-object of a domain-object.

    Args:
         domain_type:
            The domain-type of the sub-object.

        obj_id:
            The object-id of the sub-object.

        parent_domain_type:
            The domain-type of the parent object.

        parent_id:
            The object-id of the parent object.

    Examples:
        >>> sub_object_href('host', 'localhost', 'folder_config', 'stuff')
        '/objects/folder_config/stuff/host/localhost'

    Returns:
        The href as a string.
    """
    return f"/objects/{parent_domain_type}/{url_safe(parent_id)}/{domain_type}/{url_safe(obj_id)}"


def collection_href(domain_type: DomainType, name: str = "all") -> str:
    """Constructs a href to a collection.

    Please note that domain-types can have multiple collections.

    Args:
        domain_type:
            The domain-type of the collection

        name:
            The name of the collection itself.

    Examples:

        >>> collection_href('folder_config', 'all')
        '/domain-types/folder_config/collections/all'

    Returns:
        The href as a string

    """
    return f"/domain-types/{domain_type}/collections/{url_safe(name)}"


def object_action_href(
    domain_type: DomainType,
    obj_id: int | str,
    action_name: str,
    query_params: list[tuple[str, str]] | None = None,
) -> str:
    """Construct a href of a domain-object action.

    Args:
        domain_type:
            The domain-type of the object.

        obj_id:
            The object-id of the domain-object.

        action_name:
            The action-name to link to.

        query_params:
            The query parameters to be included with the action

    Examples:

        Don't try this at home. ;-)

        >>> object_action_href('folder_config', 'root', 'delete')
        '/objects/folder_config/root/actions/delete/invoke'

        >>> object_action_href('folder_config', 'root', 'delete',
        ... query_params=[('test', 'value one'), ('key', 'result')])
        '/objects/folder_config/root/actions/delete/invoke?test=value+one&key=result'

    Returns:
        The href.

    """
    base_href = f"/objects/{domain_type}/{obj_id}/actions/{action_name}/invoke"
    if query_params:
        params_part = "&".join(
            (f"{key}={quote(value, safe=' ').replace(' ', '+')}" for key, value in query_params)
        )
        return f"{base_href}?{params_part}"
    return base_href


def object_href(
    domain_type: DomainType,
    obj_id: int | str,
) -> str:
    """Constructs a href to a domain-object.

    Args:
        domain_type:
            The domain type of the object.

        obj_id:
            The identifier of the object

    Examples:

        >>> object_href('folder_config', 5)
        '/objects/folder_config/5'

        >>> object_href('folder_config', "5")
        '/objects/folder_config/5'

    Returns:
        The URL.

    """
    return f"/objects/{domain_type}/{url_safe(obj_id)}"


def url_safe(part: int | str) -> str:
    """Quote a part of the URL.

    This is necessary because as it is a string, it may contain characters like '/' which
    separates a URL path segment. This will lead to strange 404 errors if not handled correctly.

    We therefore quote these characters here.

    Args:
        part:
            The part of the URL to be escaped.

    Returns:
        An possibly escaped URL part.

    Examples:

        >>> url_safe('{variable}')
        '{variable}'

        >>> url_safe('{variable_name}')
        '{variable_name}'

        >>> url_safe('Filesystem /boot')
        'Filesystem%2520%252Fboot'

    """
    _part = str(part)
    # We don't want to escape variable templates.
    if re.match("^[{][a-z_]+[}]$", _part):
        return _part
    return quote(quote(_part, safe=""))


def domain_object(
    domain_type: DomainType,
    identifier: str,
    title: str,
    members: dict[str, Any] | None = None,
    extensions: dict[str, Any] | None = None,
    editable: bool = True,
    deletable: bool = True,
    links: list[LinkType] | None = None,
    self_link: LinkType | None = None,
    include_links: bool = True,
) -> DomainObject:
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

        self_link:
            (optional) The manually provided self link. If not provided, the self link is
            automatically generated

        include_links:
            (optional) A flag which governs if the links should be included in the output. Defaults
            to True.

    """
    uri = object_href(domain_type, identifier)
    if members is None:
        members = {}

    _links = []
    if include_links:
        _links.append(self_link if self_link is not None else link_rel("self", uri, method="get"))
        if editable:
            _links.append(link_rel(".../update", uri, method="put"))
        if deletable:
            _links.append(link_rel(".../delete", uri, method="delete"))
        if links:
            _links.extend(links)

    out: DomainObject = {
        "domainType": domain_type,
        "id": identifier,
        "title": title,
        "links": _links,
        "members": members,
    }
    if extensions is not None:
        out["extensions"] = extensions

    return out


def collection_object(
    domain_type: DomainType,
    value: list[CollectionItem] | list[LinkType] | list[DomainObject],
    links: list[LinkType] | None = None,
    extensions: dict[str, Any] | None = None,
) -> CollectionObject:
    """A collection object as specified in C-115 (Page 121)

    Args:
        domain_type:
            The domain-type of the collection.

        value:
            A list of objects. These may be either links or inlined domain-objects.

        links:
            A list of links specified elsewhere in this file.

        extensions:
            Optionally, arbitrary keys to send to the client.

    Returns:
        A collection object.

    """
    if extensions is None:
        extensions = {}
    _links = [
        link_rel("self", collection_href(domain_type)),
    ]
    if links is not None:
        _links.extend(links)
    return {
        "id": domain_type,
        "domainType": domain_type,
        "links": _links,
        "value": value,
        "extensions": extensions,
    }


def link_endpoint(
    module_name: str,
    rel: LinkRelation,
    parameters: dict[str, str],
) -> LinkType:
    """Link to a specific endpoint by name.

    Args:
        module_name:
            The Python dotted path name, where the endpoint to be linked to, is defined.

        rel:
            The endpoint's rel-name.

        parameters:
            A dict, mapping parameter names to their desired values. e.g. if the link should have
            "/foo/{baz}" rendered to "/foo/bar", this mapping should be {'baz': 'bar'}.

    """
    endpoint = endpoint_registry.lookup(module_name, rel, parameters)
    return link_rel(
        href=endpoint["endpoint"].make_url(parameters),
        rel=endpoint["rel"],
        method=endpoint["method"],
    )


def collection_item(
    domain_type: DomainType,
    identifier: str,
    title: str,
    collection_name: str = "all",
) -> LinkType:
    """A link for use in a collection object.

    Args:
        domain_type:
            The domain type of the object in the collection.

        identifier:
            The unique identifer which is able to identify this object.

        title:
            A human-readable description or title of the object.

        collection_name:
            The name of the collection. Domain types can have multiple collections, this enables
            us to link to the correct one properly.

    Returns:
        A LinkType

    """
    return link_rel(
        rel=".../value",
        parameters={"collection": collection_name},
        href=object_href(domain_type, identifier),
        profile=".../object",
        method="get",
        title=title,
    )


def action_parameter(action, parameter, friendly_name, optional, pattern):
    return (
        action,
        {
            "id": f"{action}-{parameter}",
            "name": parameter,
            "friendlyName": friendly_name,
            "optional": optional,
            "pattern": pattern,
        },
    )


def hash_of_dict(dict_: Mapping[str, Any]) -> ETagHash:
    """Build a sha256 hash over a dictionary's content.

    Keys are sorted first to ensure a stable hash.

    Examples:
        >>> hash_of_dict({'a': 'b', 'c': 'd'})
        '88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589'

    Args:
        dict_ (dict): A dictionary.

    Returns:
        ETagHash

    """

    def _update(_hash_obj, _d):
        if isinstance(_d, list | tuple):
            for value in _d:
                _update(_hash_obj, value)
        elif isinstance(_d, dict):
            for key, value in sorted(_d.items()):
                _hash_obj.update(key.encode("utf-8"))
                if isinstance(value, dict | list | tuple):
                    _update(_hash_obj, value)
                elif isinstance(value, bool):
                    _hash_obj.update(str(value).lower().encode("utf-8"))
                else:
                    _hash_obj.update(str(value).encode("utf-8"))
        else:
            _hash_obj.update(str(_d).encode("utf-8"))

    _hash = hashlib.sha256()
    _update(_hash, dict_)
    return ETagHash(_hash.hexdigest())


def etag_of_dict(dict_: Mapping[str, Any]) -> ETags:
    """Build a sha256 hash over a dictionary's content.

    Keys are sorted first to ensure a stable hash.

    Examples:
        >>> etag_of_dict({'a': 'b', 'c': 'd'})
        <ETags '"88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589"'>

        >>> etag_of_dict({'c': 'd', 'a': 'b'})
        <ETags '"88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589"'>

        >>> etag_of_dict({'a': 'b', 'c': {'d': {'e': 'f'}}})
        <ETags '"bef57ec7f53a6d40beb640a780a639c83bc29ac8a9816f1fc6c5c6dcd93c4721"'>

        >>> etag_of_dict({'a': [{'b': 1, 'd': 2}, {'d': 2, 'b': 3}]})
        <ETags '"6ea899bec9b061d54f1f8fcdb7405363126c0e96d198d09792eff0996590ee3e"'>

    Args:
        dict_ (dict): A dictionary.

    Returns:
        ETags instance.

    """

    return ETags(strong_etags=[hash_of_dict(dict_)])


def response_with_etag_created_from_dict(response: Response, dict_: Mapping[str, Any]) -> Response:
    """Add an ETag header to the response and return the updated response.
    The ETag header is an ETagHash generated from the dict passed in.
    """
    response.headers.add("ETag", etag_of_dict(dict_).to_header())
    return response
