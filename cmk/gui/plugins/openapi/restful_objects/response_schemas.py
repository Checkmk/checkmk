#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from marshmallow import Schema, fields  # type: ignore[import]
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui.plugins.openapi import plugins

# TODO: Add Enum Field for http methods, action result types and similar fields which can only hold
#       distinct values


class ApiError(Schema):
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


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(description="The user's name")
    created = fields.DateTime(dump_only=True,
                              default=dt.datetime.utcnow,
                              doc_default="The current datetime")


class Link(Schema):
    """A Link representation according to A-24 (2.7)

    """
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
        pattern="get|put|post|delete",
        example="get",
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


class Linkable(Schema):
    links = fields.List(
        fields.Nested(Link),
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
    value = fields.List(fields.Nested(Link()))


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
    id = fields.String()
    title = fields.String()
    members = fields.Nested(ObjectMemberDict())


class FolderMembers(Schema):
    hosts = fields.Nested(
        ObjectPropertyMember(),
        description="A list of links pointing to the actual host-resources.",
    )
    move = fields.Nested(
        ObjectActionMember(),
        description="An action which triggers the move of this folder to another folder.",
    )


class Folder(Linkable):
    domainType = fields.Constant(
        "folder",
        required=True,
    )
    id = fields.String()
    title = fields.String()
    members = fields.Nested(FolderMembers(),)


class MoveFolder(Schema):
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


class HostMembers(Schema):
    folder = fields.Nested(
        ObjectPropertyMember(),
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array.")


class Host(Linkable):
    domainType = fields.Constant(
        "host",
        required=True,
    )
    id = fields.String()
    title = fields.String()
    members = fields.Nested(HostMembers, description="All the members of the host object.")


class ObjectAction(Linkable):
    parameters = fields.Nested(Parameter)


class DomainObjectCollection(Linkable):
    value = fields.List(fields.Nested(Link))


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


class InstalledVersions(Schema):
    site = fields.String(description="The site where this API call was made on.",
                         example="production")
    group = fields.String(description="The Apache WSGI application group this call was made on.",
                          example="de")
    versions = fields.Dict(description="Some version numbers", example={"checkmk": "1.8.0p1"})
    edition = fields.String(description="The Checkmk edition.", example="raw")
    demo = fields.Bool(description="Whether this is a demo version or not.", example=False)


class VersionCapabilities(Schema):
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


class Version(Link):
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
