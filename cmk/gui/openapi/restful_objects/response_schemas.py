#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
import logging

from marshmallow import Schema
from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

# TODO: Add Enum Field for http methods, action result types and similar fields which can only hold
#       distinct values

_logger = logging.getLogger(__name__)


class UserSchema(BaseSchema):
    id = fields.Integer(dump_only=True)
    name = fields.String(description="The user's name")
    created = fields.DateTime(
        dump_only=True,
        format="iso8601",
        dump_default=dt.datetime.utcnow,
        doc_default="The current datetime",
    )


class LinkSchema(BaseSchema):
    """A Link representation according to A-24 (2.7)"""

    domainType = fields.Constant("link", required=True)
    rel = fields.String(
        description=(
            "Indicates the nature of the relationship of the related resource to the "
            "resource that generated this representation"
        ),
        required=True,
        example="self",
    )
    href = fields.String(
        description=(
            "The (absolute) address of the related resource. Any characters that are "
            "invalid in URLs must be URL encoded."
        ),
        required=True,
        example="https://.../api_resource",
    )
    method = fields.String(
        description="The HTTP method to use to traverse the link (get, post, put or delete)",
        required=True,
        enum=["GET", "PUT", "POST", "DELETE"],
        example="GET",
    )
    type = fields.String(
        description="The content-type that the linked resource will return",
        required=True,
        example="application/json",
    )
    title = fields.String(
        description=(
            "string that the consuming application may use to render the link without "
            "having to traverse the link in advance"
        ),
        allow_none=True,
        example="The object itself",
    )
    body_params = fields.Dict(
        description=(
            "A map of values that shall be sent in the request body. If this is present,"
            "the request has to be sent with a content-type of 'application/json'."
        ),
        required=False,
    )


class Linkable(BaseSchema):
    links = fields.List(
        fields.Nested(LinkSchema),
        required=True,
        description="list of links to other resources.",
        example=None,
    )


class Parameter(Linkable):
    id = fields.String(
        description=(
            "the Id of this action parameter (typically a concatenation of the parent "
            "action Id with the parameter name)"
        ),
        required=True,
        example="folder-move",
    )
    number = fields.Integer(
        description="the number of the parameter (starting from 0)", required=True, example=0
    )
    name = fields.String(
        description="the name of the parameter", required=True, example="destination"
    )
    friendlyName = fields.String(
        description="the action parameter name, formatted for rendering in a UI.",
        required=True,
        example="The destination folder id",
    )
    description = fields.String(
        description="a description of the action parameter, e.g. to render as a tooltip.",
        required=False,
        example="The destination",
    )
    optional = fields.Boolean(
        description="indicates whether the action parameter is optional",
        required=False,
        example=False,
    )

    # for string only
    format = fields.String(
        description=(
            "for action parameters requiring a string or number value, indicates how to"
            " interpret that value A2.5."
        ),
        required=False,
    )
    maxLength = fields.Integer(
        description=(
            "for string action parameters, indicates the maximum allowable length. A "
            "value of 0 means unlimited."
        ),
        required=False,
    )
    pattern = fields.String(
        description=(
            "for string action parameters, indicates a regular expression for the "
            "property to match."
        ),
        required=False,
    )


class ObjectMemberBase(Linkable):
    id = fields.String(required=True)
    disabledReason = fields.String(
        description=(
            'Provides the reason (or the literal "disabled") why an object property or '
            "collection is un-modifiable, or, in the case of an action, unusable (and "
            "hence no links to mutate that member's state, or invoke the action, are "
            "provided)."
        ),
        allow_none=True,
    )
    invalidReason = fields.String(
        description=(
            'Provides the reason (or the literal "invalid") why a proposed value for a '
            "property, collection or action argument is invalid. Appears within an "
            "argument representation 2.9 returned as a response."
        ),
        example="invalid",
        allow_none=True,
    )
    x_ro_invalidReason = fields.String(
        data_key="x-ro-invalidReason",
        description=(
            "Provides the reason why a SET OF proposed values for properties or arguments "
            "is invalid."
        ),
        allow_none=True,
    )


class ObjectCollectionMember(ObjectMemberBase):
    memberType = fields.Constant("collection")
    value = fields.List(fields.Nested(LinkSchema()))
    name = fields.String(example="important_values")
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )


class ObjectProperty(Linkable):
    id = fields.String(description="The unique name of this property, local to this domain type.")
    value = fields.List(
        fields.String(),
        description="The value of the property. In this case a list.",
    )
    extensions = fields.Dict(
        description="Additional attributes alongside the property.",
    )


class ObjectPropertyMember(ObjectMemberBase):
    memberType = fields.Constant("property")
    name = fields.String(example="important")
    value = fields.String(example="the value")
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )


class ObjectActionMember(ObjectMemberBase):
    memberType = fields.Constant("action")
    parameters = fields.Dict()
    name = fields.String(example="frobnicate_foo")
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )


class ObjectMember(OneOfSchema):
    type_field = "memberType"
    type_schemas = {
        "action": ObjectActionMember,
        "property": ObjectPropertyMember,
        "collection": ObjectCollectionMember,
    }


class ActionResultBase(Linkable):
    resultType: gui_fields.Field = fields.String(
        enum=["object", "scalar"],
        description="The type of the result.",
    )
    extensions = fields.Dict(
        example={"some": "values"},
        description="Some attributes alongside the result.",
    )


class ActionResultObject(ActionResultBase):
    result = fields.Nested(
        Schema.from_dict(
            {
                "links": fields.List(
                    fields.Nested(LinkSchema),
                    required=True,
                ),
                "value": fields.Dict(
                    required=True,
                    example={"duration": "5 seconds."},
                ),
            },
            name="ActionResultObjectValue",
        ),
        description="The result of the action. In this case, an object.",
    )


class ActionResultScalar(ActionResultBase):
    result = fields.Nested(
        Schema.from_dict(
            {
                "links": fields.List(
                    fields.Nested(LinkSchema),
                    required=True,
                ),
                "value": fields.String(
                    required=True,
                    example="Done.",
                ),
            },
            name="ActionResultScalarValue",
        ),
        description="The scalar result of the action.",
    )


class ActionResult(OneOfSchema):
    type_field = "resultType"
    type_schemas = {
        "object": ActionResultObject,
        "scalar": ActionResultScalar,
    }


class DomainObjectBase(BaseSchema):
    domainType: gui_fields.Field = fields.String(
        required=True,
        description='The "domain-type" of the object.',
    )
    # Generic things to ease development. Should be changed for more concrete schemas.
    id = fields.String(
        description="The unique identifier for this domain-object type.",
    )
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )
    members: gui_fields.Field = fields.Dict(
        description="The container for external resources, like linked foreign objects or actions.",
    )
    extensions: gui_fields.Field = fields.Dict(
        description="All the attributes of the domain object."
    )


class DomainObject(DomainObjectBase, Linkable): ...


class MoveFolder(BaseSchema):
    destination = fields.String(
        description=(
            "The folder-id of the folder to which this folder shall be moved to. May "
            "be 'root' for the root-folder."
        ),
        pattern="^[a-fA-F0-9]{32}$|root",
        example="root",
        required=True,
    )


class Configuration(DomainObject):
    domainType = fields.Constant("config", required=True)


class SiteStateMembers(BaseSchema):
    sites = fields.Dict()


class SiteState(Linkable):
    domainType = fields.Constant("site-state", required=True)
    members = fields.Nested(SiteStateMembers, description="All the members of the host object.")


class ObjectAction(Linkable):
    parameters = fields.Nested(Parameter)


class TypeSchemas(dict):
    """This automatically creates entries with the default value."""

    def get(self, key, default=None):
        return self[key]

    def __missing__(self, key):
        return DomainObject


class CollectionItem(OneOfSchema):
    type_schemas = TypeSchemas({"link": LinkSchema})
    type_field = "domainType"
    type_field_remove = False


class DomainObjectBaseCollection(BaseSchema):
    id = fields.String(
        description="The name of this collection.",
        load_default="all",
    )
    domainType: gui_fields.Field = fields.String(
        description="The domain type of the objects in the collection."
    )
    title = fields.String(
        description="A human readable title of this object. Can be used for user interfaces.",
    )
    value: gui_fields.Field = fields.Nested(
        CollectionItem,
        description="The collection itself. Each entry in here is part of the collection.",
        many=True,
    )
    extensions = fields.Dict(description="Additional attributes alongside the collection.")


class DomainObjectCollection(DomainObjectBaseCollection, Linkable): ...


class VersionCapabilities(BaseSchema):
    blobsClobs = fields.Boolean(
        required=False,
        description="attachment support",
    )
    deleteObjects = fields.Boolean(
        required=False,
        description=(
            "deletion of persisted objects through the DELETE Object resource C14.3, see A3.5"
        ),
    )
    domainModel = fields.String(
        required=False,
        description=(
            'different domain metadata representations. A value of "selectable" means '
            "that the reserved x-domain-model query parameter is supported, see A3.1"
        ),
    )
    protoPersistentObjects = fields.Boolean()
    validateOnly = fields.Boolean(
        required=False,
        description="the reserved x-ro-validate-only query parameter, see A3.2",
    )


class Version(LinkSchema):
    specVersion = fields.String(
        description=(
            'The "major.minor" parts of the version of the spec supported by this '
            'implementation, e.g. "1.0"'
        ),
        required=False,
    )
    implVersion = fields.String(
        description=(
            "(optional) Version of the implementation itself (format is specific to "
            "the implementation)"
        ),
        required=False,
    )
    additionalCapabilities = fields.Nested(VersionCapabilities)


class AgentObject(DomainObject):
    domainType = fields.Constant(
        "agent",
        description="The domain type of the object.",
    )


class AgentCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "agent",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(AgentObject),
        description="A list of agent objects.",
    )


class JobLogs(BaseSchema):
    result = fields.List(
        fields.String(),
        description="The list of result related logs",
    )
    progress = fields.List(
        fields.String(),
        description="The list of progress related logs",
    )


class BackgroundJobStatus(BaseSchema):
    active = fields.Boolean(
        required=True,
        description="This field indicates if the background job is active or not.",
        example=True,
    )
    state = fields.String(
        required=True,
        description="This field indicates the current state of the background job.",
        enum=["initialized", "running", "finished", "stopped", "exception"],
        example="initialized",
    )
    logs = fields.Nested(
        JobLogs,
        required=True,
        description="Logs related to the background job.",
        example={"result": ["result1"], "progress": ["progress1"]},
    )


class VerificationRequest(BaseSchema):
    """License verification request"""

    VERSION = fields.String(required=True, description="The version of the request", example="3.0")
    request_id = fields.String(
        required=True,
        description="The ID of the request",
        example="df17e557-0daf-4b78-b9f2-f3550252a8b5",
    )
    instance_id = fields.String(
        required=True,
        description="The ID of the instance the request is for",
        example="6b9e78d1-de99-46ef-9644-32ee33a2b489",
    )
    created_at = fields.Integer(
        required=True, description="The creation timestamp", example=1690379907
    )
    upload_origin = fields.String(
        required=True, description="How the request was uploaded", example="manual"
    )
    raw_reports = fields.List(
        fields.Dict,
        required=True,
        description="The license usage reports",
        example=[{}],
    )
