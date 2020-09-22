#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.defines import weekday_ids
from cmk.gui.plugins.openapi import fields, plugins
from cmk.gui.plugins.openapi.utils import BaseSchema

# TODO: Add Enum Field for http methods, action result types and similar fields which can only hold
#       distinct values


class ApiError(BaseSchema):
    code = fields.Integer(
        description="The HTTP status code.",
        required=True,
        example=404,
    )
    message = fields.Str(
        description="Detailed information on what exactly went wrong.",
        required=True,
        example="The resource could not be found.",
    )
    title = fields.Str(
        description="A summary of the problem.",
        required=True,
        example="Not found",
    )
    errors = fields.List(
        fields.String(),
        allow_none=True,
        description="Optionally a list of errors used for debugging.",
        example=None,
    )


class UserSchema(BaseSchema):
    id = fields.Int(dump_only=True)
    name = fields.Str(description="The user's name")
    created = fields.DateTime(dump_only=True,
                              format="iso8601",
                              default=dt.datetime.utcnow,
                              doc_default="The current datetime")


class LinkSchema(BaseSchema):
    """A Link representation according to A-24 (2.7)

    """
    domainType = fields.Constant("link", required=True)
    rel = fields.String(
        description=("Indicates the nature of the relationship of the related resource to the "
                     "resource that generated this representation"),
        required=True,
        example="self",
    )
    href = fields.Str(
        description=("The (absolute) address of the related resource. Any characters that are "
                     "invalid in URLs must be URL encoded."),
        required=True,
        example="https://.../api_resource",
    )
    method = fields.String(
        description="The HTTP method to use to traverse the link (get, post, put or delete)",
        required=True,
        pattern="GET|PUT|POST|DELETE",
        example="GET",
    )
    type = fields.String(
        description="The media type that the linked resource will return",
        required=True,
        example="application/json",
    )
    title = fields.String(
        description=("string that the consuming application may use to render the link without "
                     "having to traverse the link in advance"),
        allow_none=True,
        example="The object itself",
    )
    arguments = fields.Dict(
        description=("map that may be used as the basis for any data (arguments or properties) "
                     "required to follow the link."),
        allow_none=True,
    )


class Linkable(BaseSchema):
    links = fields.List(
        fields.Nested(LinkSchema),
        required=True,
        description="list of links to other resources.",
    )


class Parameter(Linkable):
    id = fields.String(
        description=("the Id of this action parameter (typically a concatenation of the parent "
                     "action Id with the parameter name)"),
        required=True,
        example='folder-move',
    )
    number = fields.Int(description="the number of the parameter (starting from 0)",
                        required=True,
                        example=0)
    name = fields.String(description="the name of the parameter",
                         required=True,
                         example='destination')
    friendlyName = fields.String(
        description="the action parameter name, formatted for rendering in a UI.",
        required=True,
        example='The destination folder id',
    )
    description = fields.String(
        description="a description of the action parameter, e.g. to render as a tooltip.",
        required=False,
        example='The destination')
    optional = fields.Bool(
        description="indicates whether the action parameter is optional",
        required=False,
        example=False,
    )

    # for string only
    format = fields.String(
        description=("for action parameters requiring a string or number value, indicates how to"
                     " interpret that value A2.5."),
        required=False,
    )
    maxLength = fields.Int(
        description=("for string action parameters, indicates the maximum allowable length. A "
                     "value of 0 means unlimited."),
        required=False,
    )
    pattern = fields.String(
        description=("for string action parameters, indicates a regular expression for the "
                     "property to match."),
        required=False,
    )


class ObjectMemberBase(Linkable):
    id = fields.String(required=True)
    disabledReason = fields.String(
        description=('Provides the reason (or the literal "disabled") why an object property or '
                     'collection is un-modifiable, or, in the case of an action, unusable (and '
                     'hence no links to mutate that member\'s state, or invoke the action, are '
                     'provided).'),
        allow_none=True,
    )
    invalidReason = fields.String(
        description=('Provides the reason (or the literal "invalid") why a proposed value for a '
                     'property, collection or action argument is invalid. Appears within an '
                     'argument representation 2.9 returned as a response.'),
        example="invalid",
        allow_none=True,
    )
    x_ro_invalidReason = fields.String(
        dump_to="x-ro-invalidReason",
        description=("Provides the reason why a SET OF proposed values for properties or arguments "
                     "is invalid."),
        allow_none=True,
    )


class ObjectCollectionMember(ObjectMemberBase):
    memberType = fields.Constant('collection')
    value = fields.List(fields.Nested(LinkSchema()))


class ObjectPropertyMember(ObjectMemberBase):
    memberType = fields.Constant('property')


class ObjectActionMember(ObjectMemberBase):
    memberType = fields.Constant('action')


class ObjectMember(OneOfSchema):
    type_field = 'memberType'
    type_schemas = {
        'action': ObjectActionMember,
        'property': ObjectPropertyMember,
        'collection': ObjectCollectionMember,
    }


class ObjectMemberDict(plugins.ValueTypedDictSchema):
    value_type = ObjectMember  # type: ignore[assignment]


class ActionResultBase(Linkable):
    resultType = fields.String(required=True, example='object')
    result = fields.Dict()


class ActionResultObject(ActionResultBase):
    resultType = fields.Constant('object')
    value = fields.Dict(required=True,
                        allow_none=True,
                        example={'foo': 'bar'},
                        description="The return value of this action.")


class ActionResultScalar(ActionResultBase):
    resultType = fields.Constant('scalar')
    value = fields.String(required=True,
                          allow_none=True,
                          example="Done.",
                          description="The return value of this action.")


class ActionResult(OneOfSchema):
    type_field = 'resultType'
    type_schemas = {
        'object': ActionResultObject,
    }


class AttributeDict(plugins.ValueTypedDictSchema):
    value_type = fields.String()


class DomainObject(Linkable):
    domainType = fields.String(required=True)
    # Generic things to ease development. Should be changed for more concrete schemas.
    id = fields.String()
    title = fields.String()
    members = fields.Nested(ObjectMemberDict())


class FolderMembers(BaseSchema):
    hosts = fields.Nested(
        ObjectCollectionMember(),
        description="A list of links pointing to the actual host-resources.",
    )
    move = fields.Nested(
        ObjectActionMember(),
        description="An action which triggers the move of this folder to another folder.",
    )


class FolderSchema(Linkable):
    domainType = fields.Constant(
        "folder_config",
        required=True,
    )
    id = fields.String()
    title = fields.String()
    members = fields.Nested(FolderMembers())


class ConcreteFolder(OneOfSchema):
    type_schemas = {
        'folder_config': FolderSchema,
        'link': LinkSchema,
    }
    type_field = 'domainType'


class MoveFolder(BaseSchema):
    destination = fields.String(
        description=("The folder-id of the folder to which this folder shall be moved to. May "
                     "be 'root' for the root-folder."),
        pattern="[a-fA-F0-9]{32}|root",
        example="root",
        required=True,
    )


class HostGroup(DomainObject):
    domainType = fields.Constant(
        "host_group",
        required=True,
    )


class ServiceGroup(DomainObject):
    domainType = fields.Constant(
        "service_group",
        required=True,
    )


class ContactGroup(DomainObject):
    domainType = fields.Constant(
        "contact_group",
        required=True,
    )


class Configuration(DomainObject):
    domainType = fields.Constant("config", required=True)


class SiteStateMembers(BaseSchema):
    sites = fields.Dict()


class SiteState(Linkable):
    domainType = fields.Constant("site-state", required=True)
    members = fields.Nested(SiteStateMembers, description="All the members of the host object.")


class HostMembers(BaseSchema):
    folder_config = fields.Nested(
        ConcreteFolder,
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array.")


class HostSchema(Linkable):
    domainType = fields.Constant("host_config", required=True)
    id = fields.String()
    title = fields.String()
    members = fields.Nested(HostMembers, description="All the members of the host object.")


class ConcreteHost(OneOfSchema):
    type_schemas = {
        'host_config': HostSchema,
        'link': LinkSchema,
    }
    type_field = 'domainType'


class HostCollection(Linkable):
    domainType = fields.Constant("host_config", required=True)
    id = fields.String()
    title = fields.String()
    value = fields.List(fields.Nested(ConcreteHost))


class ObjectAction(Linkable):
    parameters = fields.Nested(Parameter)


class DomainObjectCollection(Linkable):
    id = fields.String()
    domainType = fields.String()
    value = fields.List(fields.Nested(LinkSchema))
    extensions = fields.Dict()


class FolderCollection(DomainObjectCollection):
    domainType = fields.Constant("folder_config")
    value = fields.List(fields.Nested(ConcreteFolder))


class User(Linkable):
    userName = fields.Str(description="a unique user name")
    friendlyName = fields.Str(
        required=True,
        description="(optional) the user's name in a form suitable to be rendered in a UI.",
    )
    email = fields.Str(description="(optional) the user's email address, if known")
    roles = fields.List(
        fields.Str(),
        description="list of unique role names that apply to this user (can be empty).",
    )


TIME_FIELD = fields.Time(
    example="14:00",
    description="The hour of the time period.",
)


class ConcreteTimeRange(BaseSchema):
    start = TIME_FIELD
    end = TIME_FIELD


class ConcreteTimeRangeActive(BaseSchema):
    day = fields.String(description="The day for which the time ranges are specified",
                        pattern=f"{'|'.join(weekday_ids())}")
    time_ranges = fields.List(fields.Nested(ConcreteTimeRange))


class ConcreteTimePeriodException(BaseSchema):
    date = fields.Date(
        example="2020-01-01",
        description="The date of the time period exception."
        "8601 profile",
    )
    time_ranges = fields.List(
        fields.Nested(ConcreteTimeRange),
        example="[{'start': '14:00', 'end': '18:00'}]",
    )


class ConcreteTimePeriod(BaseSchema):
    alias = fields.String(description="The alias of the time period", example="alias")
    active_time_ranges = fields.List(
        fields.Nested(ConcreteTimeRangeActive),
        description="The days for which time ranges were specified",
        example={
            'day': 'all',
            'time_ranges': [{
                'start': '12:00',
                'end': '14:00'
            }]
        },
    )
    exceptions = fields.List(
        fields.Nested(ConcreteTimePeriodException),
        description="Specific day exclusions with their list of time ranges",
        example=[{
            'date': '2020-01-01',
            'time_ranges': [{
                'start': '14:00',
                'end': '18:00'
            }]
        }],
    )
    exclude = fields.List(
        fields.String(description="Name of excluding time period", example="holidays"),
        description="The collection of time period aliases whose periods are excluded",
    )


class ConcretePassword(BaseSchema):
    ident = fields.String(
        example="pass",
        description="The unique identifier for the password",
    )
    title = fields.String(
        example="Kubernetes login",
        description="The title for the password",
    )
    comment = fields.String(
        example="Kommentar",
        description="A comment for the password",
    )

    documentation_url = fields.String(
        example="localhost",
        description="The URL pointing to documentation or any other page.",
    )

    password = fields.String(
        required=True,
        example="password",
        description="The password string",
    )

    owner = fields.String(
        example="admin",
        description=
        "The owner of the password who is able to edit, delete and use existing passwords.")

    shared = fields.List(
        fields.String(
            example="all",
            description="The member the password is shared with",
        ),
        example=["all"],
        description="The list of members the password is shared with",
    )


class InstalledVersions(BaseSchema):
    site = fields.String(description="The site where this API call was made on.",
                         example="production")
    group = fields.String(description="The Apache WSGI application group this call was made on.",
                          example="de")
    versions = fields.Dict(description="Some version numbers", example={"checkmk": "1.8.0p1"})
    edition = fields.String(description="The Checkmk edition.", example="raw")
    demo = fields.Bool(description="Whether this is a demo version or not.", example=False)


class VersionCapabilities(BaseSchema):
    blobsClobs = fields.Bool(
        required=False,
        description="attachment support",
    )
    deleteObjects = fields.Bool(
        required=False,
        description=("deletion of persisted objects through the DELETE Object resource C14.3,"
                     " see A3.5"),
    )
    domainModel = fields.Str(
        required=False,
        description=('different domain metadata representations. A value of "selectable" means '
                     'that the reserved x-domain-model query parameter is supported, see A3.1'),
    )
    protoPersistentObjects = fields.Bool()
    validateOnly = fields.Bool(
        required=False,
        description="the reserved x-ro-validate-only query parameter, see A3.2",
    )


class Version(LinkSchema):
    specVersion = fields.Str(
        description=('The "major.minor" parts of the version of the spec supported by this '
                     'implementation, e.g. "1.0"'),
        required=False,
    )
    implVersion = fields.Str(
        description=("(optional) Version of the implementation itself (format is specific to "
                     "the implementation)"),
        required=False,
    )
    additionalCapabilities = fields.Nested(VersionCapabilities)
