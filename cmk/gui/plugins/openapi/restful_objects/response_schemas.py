#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from marshmallow import Schema, fields  # type: ignore
from marshmallow_oneofschema import OneOfSchema  # type: ignore

from cmk.gui.plugins.openapi import plugins


class ApiError(Schema):
    code = fields.Str(description="The HTTP status code.")
    message = fields.Str()
    title = fields.Str()


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
    )
    href = fields.Str(
        description=("The (absolute) address of the related resource. Any characters that are "
                     "invalid in URLs must be URL encoded."),
        required=True,
    )
    method = fields.String(
        description="The HTTP method to use to traverse the link (GET, POST, PUT or DELETE)",
        required=True,
    )
    type = fields.String(
        description="The media type that the linked resource will return",
        required=True,
    )
    title = fields.String(
        description=("string that the consuming application may use to render the link without "
                     "having to traverse the link in advance"),
        allow_none=True,
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
    )
    number = fields.Int(
        description="the number of the parameter (starting from 0)",
        required=True,
    )
    name = fields.String(
        description="the name of the parameter",
        required=True,
    )
    friendlyName = fields.String(
        description="the action parameter name, formatted for rendering in a UI.",
        required=True,
    )
    description = fields.String(
        description="a description of the action parameter, e.g. to render as a tooltip.",
        required=False,
    )
    optional = fields.Bool(
        description="indicates whether the action parameter is optional",
        required=False,
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
    value = fields.List(fields.String())


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


class DomainObject(Linkable):
    domainType = fields.String(required=True)
    title = fields.String()
    members = fields.Nested(ObjectMemberDict)


class Folder(DomainObject):
    domainType = fields.Constant(
        "folder",
        required=True,
    )


class HostGroup(DomainObject):
    domainType = fields.Constant(
        "host_group",
        required=True,
    )


class Host(DomainObject):
    domainType = fields.Constant(
        "host",
        required=True,
    )


class InputAttribute(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


class InputHost(Schema):
    hostname = fields.String()
    folder_id = fields.String()
    attributes = fields.Dict()


class InputHostGroup(Schema):
    name = fields.String(required=True)
    alias = fields.String()


class InputFolder(Schema):
    name = fields.String(required=True)
    title = fields.String(required=True)
    attributes = fields.List(fields.Nested(InputAttribute))


class UpdateFolder(Schema):
    title = fields.String(required=True)
    attributes = fields.List(fields.Nested(InputAttribute))


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
    # TODO: Add properties and documentation.
    pass


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
