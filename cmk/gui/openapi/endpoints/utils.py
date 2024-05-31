#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import http.client
import json
from collections.abc import Sequence
from typing import Any, Literal

from livestatus import MultiSiteConnection, SiteId

from cmk.utils import version
from cmk.utils.livestatus_helpers.queries import detailed_connection, Query
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.version import edition, Edition

from cmk.gui.customer import customer_api, CustomerIdOrGlobal
from cmk.gui.exceptions import MKHTTPException
from cmk.gui.groups import GroupName, GroupSpec, GroupSpecs, GroupType
from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects import constructors
from cmk.gui.openapi.restful_objects.type_defs import CollectionObject
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.groups import edit_group
from cmk.gui.watolib.groups_io import load_group_information
from cmk.gui.watolib.hosts_and_folders import Folder

GroupDomainType = Literal[
    "host_group_config", "contact_group_config", "service_group_config", "agent"
]


def complement_customer(details):
    if edition() is not Edition.CME:
        return details

    if "customer" in details:
        customer_id = details["customer"]
        details["customer"] = "global" if customer_api().is_global(customer_id) else customer_id
    else:  # special case where customer is set to customer_default_id which results in no-entry
        details["customer"] = customer_api().default_customer_id()
    return details


def serve_group(group, serializer) -> Response:  # type: ignore[no-untyped-def]
    response = Response()
    response.set_data(json.dumps(serializer(group)))
    if response.status_code != 204:
        response.set_content_type("application/json")
    return constructors.response_with_etag_created_from_dict(response, group)


def serialize_group_list(
    domain_type: GroupDomainType,
    collection: Sequence[GroupSpec],
) -> CollectionObject:
    return constructors.collection_object(
        domain_type=domain_type,
        value=[
            constructors.domain_object(
                domain_type=domain_type,
                title=group["alias"],
                identifier=group["id"],
            )
            for group in collection
        ],
        links=[constructors.link_rel("self", constructors.collection_href(domain_type))],
    )


def serialize_group(name: GroupDomainType) -> Any:
    def _serializer(group: dict[str, str]) -> Any:
        ident = group["id"]
        extensions = {}
        if "customer" in group:
            customer_id = group["customer"]
            extensions["customer"] = "global" if customer_id is None else customer_id
        elif edition() is Edition.CME:
            extensions["customer"] = customer_api().default_customer_id()

        extensions["alias"] = group["alias"]
        return constructors.domain_object(
            domain_type=name,
            identifier=ident,
            title=group["alias"] or ident,
            extensions=extensions,
        )

    return _serializer


def update_groups(  # type: ignore[no-untyped-def]
    group_type: GroupType, entries: list[dict[str, Any]]
):
    groups = []
    for details in entries:
        name = details["name"]
        group_details = details["attributes"]
        updated_details = updated_group_details(name, group_type, group_details)
        edit_group(name, group_type, updated_details)
        groups.append(name)

    return fetch_specific_groups(groups, group_type)


def prepare_groups(group_type: GroupType, entries: list[dict[str, Any]]) -> GroupSpecs:
    specific_existing_groups = load_group_information()[group_type]
    groups: GroupSpecs = {}
    already_existing = []
    for details in entries:
        name = details["name"]
        if name in specific_existing_groups:
            already_existing.append(name)
            continue
        group_details: GroupSpec = {"alias": details["alias"]}
        if version.edition() is version.Edition.CME:
            group_details = update_customer_info(group_details, details["customer"])
        groups[name] = group_details

    if already_existing:
        raise ProblemException(
            status=400,
            title=f"Some {group_type} groups already exist",
            detail=f"The following {group_type} group names already exist: {', '.join(already_existing)}",
        )

    return groups


def fetch_group(
    ident: str,
    group_type: GroupType,
    status: int = 404,
    message: str | None = None,
) -> GroupSpec:
    groups = load_group_information()[group_type]
    group = _retrieve_group(ident, groups, status, message)
    group["id"] = ident
    return group


def fetch_specific_groups(
    idents: list[str],
    group_type: GroupType,
    status: int = 404,
    message: str | None = None,
) -> list[GroupSpec]:
    groups = load_group_information()[group_type]
    result = []
    for ident in idents:
        group = _retrieve_group(ident, groups, status, message)
        group["id"] = ident
        result.append(group)
    return result


def _retrieve_group(
    ident: str,
    groups: GroupSpecs,
    status: int,
    message: str | None,
) -> GroupSpec:
    try:
        group = groups[ident].copy()
    except KeyError as exc:
        if message is None:
            message = str(exc)
        raise ProblemException(status, http.client.responses[status], message)
    return group


@contextlib.contextmanager
def may_fail(  # type: ignore[no-untyped-def]
    exc_type: type[Exception] | tuple[type[Exception], ...],
    status: int | None = None,
):
    """Context manager to make Exceptions REST-API safe

        Examples:
            >>> try:
            ...     with may_fail(ValueError, status=404):
            ...          raise ValueError("Nothing to see here, move along.")
            ... except ProblemException as _exc:
            ...     _exc.to_problem().data
            b'{"title": "The operation has failed.", "status": 404, \
"detail": "Nothing to see here, move along."}'

            >>> from cmk.gui.exceptions import MKUserError
            >>> try:
            ...     with may_fail(MKUserError):
            ...        raise MKUserError(None, "There is an activation already running.",
            ...                          status=409)
            ... except ProblemException as _exc:
            ...     _exc.to_problem().data
            b'{"title": "The operation has failed.", "status": 409, \
"detail": "There is an activation already running."}'

            >>> from cmk.gui.exceptions import MKAuthException
            >>> try:
            ...     with may_fail(MKAuthException, status=401):
            ...        raise MKAuthException("These are not the droids that you are looking for.")
            ... except ProblemException as _exc:
            ...     _exc.to_problem().data
            b'{"title": "The operation has failed.", "status": 401, \
"detail": "These are not the droids that you are looking for."}'

    """

    def _get_message(e):
        if hasattr(e, "message"):
            return e.message

        return str(e)

    try:
        yield
    except exc_type as exc:
        if isinstance(exc, MKHTTPException):
            status = exc.status
        elif status is None:
            status = 400
        raise ProblemException(
            status=status,
            title="The operation has failed.",
            detail=_get_message(exc),
        ) from exc


def update_customer_info(
    attributes: dict[str, Any], customer_id: CustomerIdOrGlobal, remove_provider: bool = False
) -> dict[str, Any]:
    """Update the attributes with the correct customer_id

    Args:
        attributes:
            the attributes of the to save/edit instance
        customer_id:
            the internal customer id
        remove_provider:
            Bool which decides if the customer entry should be removed if set to the customer_default_id

    """
    # None is a valid customer_id used for 'Global' configuration
    if remove_provider and customer_id == customer_api().default_customer_id():
        attributes.pop("customer", None)
        return attributes

    attributes["customer"] = customer_id
    return attributes


def group_edit_details(body: GroupSpec) -> GroupSpec:
    group_details: GroupSpec = {k: v for k, v in body.items() if k != "customer"}

    if version.edition() is version.Edition.CME and "customer" in body:
        group_details = update_customer_info(group_details, body["customer"])
    return group_details


def updated_group_details(
    name: GroupName, group_type: GroupType, changed_details: GroupSpec
) -> GroupSpec:
    """Updates the group details without saving

    Args:
        name:
            str representing the id of the group
        group_type:
            str representing the group type
        changed_details:
            dict containing the attributes which should be changed from the current group

    Returns:
        the to-be-saved dict with the changed attributes

    """
    group = fetch_group(name, group_type)
    changed_details = group_edit_details(changed_details)
    group.update(changed_details)
    return group


def folder_slug(folder: Folder) -> str:
    """Create a tilde separated path identifier to be used in URLs

    Args:
        folder:
            The folder instance for which to generate the URL.

    Returns:
        A path looking like this: `~folder~subfolder~leaf_folder`

    """
    return "~" + folder.path().rstrip("/").replace("/", "~")


def get_site_id_for_host(connection: MultiSiteConnection, host_name: str) -> SiteId:
    with detailed_connection(connection) as conn:
        return Query(columns=[Hosts.name], filter_expr=Hosts.name.op("=", host_name)).value(conn)
