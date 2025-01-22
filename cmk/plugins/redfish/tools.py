#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tools used by all Redfish special agents"""

from redfish.messages import (
    get_error_messages,
    get_messages_detail,
    RedfishOperationFailedError,
    RedfishPasswordChangeRequiredError,
    search_message,
)


class RedfishCollectionNotFoundError(Exception):
    """
    Raised when the specified collection is not found (HTTP Status = 404)
    """


class RedfishCollectionMemberNotFoundError(Exception):
    """
    Raised when the specified member is not found (HTTP Status = 404)
    """


def _verify_response(response):
    """
    Verifies a response and raises an exception if there was a failure

    Args:
        response: The response to verify
    """

    if response.status >= 400:
        messages_detail = get_messages_detail(response)
        exception_string = get_error_messages(messages_detail)
        message_item = search_message(messages_detail, "Base", "PasswordChangeRequired")
        if message_item is not None:
            raise RedfishPasswordChangeRequiredError(
                f"Operation failed: HTTP {response.status}\n{exception_string}",
                message_item["MessageArgs"][0],
            )
        raise RedfishOperationFailedError(
            f"Operation failed: HTTP {response.status}\n{exception_string}"
        )


def get_object_ids(context, object_dict, object_name):
    """
    Get all ids of an collection object

    Args:
        context: The Redfish client object with an open session
        object_dict: object data
        object_name: name of the object the ids should collected from

    Returns:
        A list of identifiers of the members of the object collection
    """
    collection_uri = object_dict.dict[object_name]["@odata.id"]
    avail_members = []
    collection = context.get(collection_uri)
    if collection.status == 404:
        raise RedfishCollectionNotFoundError(
            f"Service does not contain a collection at URI {collection_uri}"
        )
    _verify_response(collection)
    while True:
        for member in collection.dict["Members"]:
            avail_members.append(member["@odata.id"].strip("/").split("/")[-1])
        if "Members@odata.nextLink" not in collection.dict:
            break
        collection = context.get(collection.dict["Members@odata.nextLink"])
        _verify_response(collection)

    return avail_members
