#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from marshmallow import Schema
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.defines import weekday_ids

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

from cmk import fields

# TODO: Add Enum Field for http methods, action result types and similar fields which can only hold
#       distinct values


class ApiError(BaseSchema):
    """This is the base class for all API errors."""

    code = fields.Integer(
        description="The HTTP status code.",
        required=True,
        example=404,
    )
    message = fields.String(
        description="Detailed information on what exactly went wrong.",
        required=True,
        example="The resource could not be found.",
    )
    title = fields.String(
        description="A summary of the problem.",
        required=True,
        example="Not found",
    )
    _fields = fields.Dict(
        data_key="fields",  # mypy, due to attribute "fields" being used in marshmallow.Schema
        keys=fields.String(description="The field name"),
        values=fields.List(fields.String(description="The error messages")),
        description="Detailed error messages on all fields failing validation.",
        required=False,
    )
    ext: fields.Field = fields.Dict(
        keys=fields.String(description="The key name"),
        values=fields.String(description="The value"),
        description="Additional information about the error.",
        required=False,
    )


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
        pattern="GET|PUT|POST|DELETE",
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
        description="A human readable title of this object. Can be used for " "user interfaces.",
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
        description="A human readable title of this object. Can be used for " "user interfaces.",
    )


class ObjectActionMember(ObjectMemberBase):
    memberType = fields.Constant("action")
    parameters = fields.Dict()
    name = fields.String(example="frobnicate_foo")
    title = fields.String(
        description="A human readable title of this object. Can be used for " "user interfaces.",
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


class DomainObject(Linkable):
    domainType: gui_fields.Field = fields.String(
        required=True,
        description='The "domain-type" of the object.',
    )
    # Generic things to ease development. Should be changed for more concrete schemas.
    id = fields.String(
        description="The unique identifier for this domain-object type.",
    )
    title = fields.String(
        description="A human readable title of this object. Can be used for " "user interfaces.",
    )
    members: gui_fields.Field = fields.Dict(
        description="The container for external resources, like linked foreign objects or actions.",
    )
    extensions: gui_fields.Field = fields.Dict(
        description="All the attributes of the domain object."
    )


class HostExtensions(BaseSchema):
    folder = gui_fields.FolderField(
        description="The folder, in which this host resides.",
    )
    attributes = gui_fields.attributes_field(
        "host",
        "view",
        description="Attributes of this host.",
        example={"ipaddress": "192.168.0.123"},
    )
    effective_attributes = fields.Dict(
        description="All attributes of this host and all parent folders. Format may change!",
        allow_none=True,
        example={"tag_snmp_ds": None},
    )
    is_cluster = fields.Boolean(
        description="If this is a cluster host, i.e. a container for other hosts.",
    )
    is_offline = fields.Boolean(
        description="Whether the host is offline",
    )
    cluster_nodes = fields.List(
        gui_fields.HostField(),
        allow_none=True,
        load_default=None,
        description="In the case this is a cluster host, these are the cluster nodes.",
    )


class FolderMembers(BaseSchema):
    hosts = fields.Nested(
        ObjectCollectionMember(),
        description="A list of links pointing to the actual host-resources.",
    )
    move = fields.Nested(
        ObjectActionMember(),
        description="An action which triggers the move of this folder to another folder.",
    )


class FolderExtensions(BaseSchema):
    path = fields.String(
        description="The full path of this folder, slash delimited.",
    )
    attributes = gui_fields.attributes_field(
        "folder",
        "view",
        description=(
            "The folder's attributes. Hosts placed in this folder will inherit " "these attributes."
        ),
    )


class FolderSchema(Linkable):
    domainType = fields.Constant("folder_config", description="The domain type of the object.")
    id = fields.String(description="The full path of the folder, tilde-separated.")
    title = fields.String(description="The human readable title for this folder.")
    members = fields.Nested(
        FolderMembers(),
        description="Specific collections or actions applicable to this object.",
    )
    extensions = fields.Nested(
        FolderExtensions(),
        description="Data and Meta-Data of this object.",
    )


class MoveFolder(BaseSchema):
    destination = fields.String(
        description=(
            "The folder-id of the folder to which this folder shall be moved to. May "
            "be 'root' for the root-folder."
        ),
        pattern="[a-fA-F0-9]{32}|root",
        example="root",
        required=True,
    )


class HostGroup(DomainObject):
    domainType = fields.Constant(
        "host_group", required=True, description="The domain type of the object."
    )


class ServiceGroup(DomainObject):
    domainType = fields.Constant(
        "service_group", required=True, description="The domain type of the object."
    )


class ContactGroup(DomainObject):
    domainType = fields.Constant(
        "contact_group", required=True, description="The domain type of the object."
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
        FolderSchema(),
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array.",
    )


class HostConfigSchema(DomainObject):
    domainType = fields.Constant(
        "host_config", required=True, description="The domain type of the object."
    )
    members = fields.Nested(HostMembers, description="All the members of the host object.")
    extensions = fields.Nested(
        HostExtensions,
        description="All the data and metadata of this host.",
    )


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


class ConcreteHostTagGroup(DomainObject):
    domainType = fields.Constant(
        "host_tag_group",
        required=True,
        description="The domain type of the object.",
    )


class DomainObjectCollection(Linkable):
    id = fields.String(
        description="The name of this collection.",
        load_default="all",
    )
    domainType: gui_fields.Field = fields.String(
        description="The domain type of the objects in the collection."
    )
    title = fields.String(
        description="A human readable title of this object. Can be used for " "user interfaces.",
    )
    value: gui_fields.Field = fields.Nested(
        CollectionItem,
        description="The collection itself. Each entry in here is part of the collection.",
        many=True,
    )
    extensions = fields.Dict(description="Additional attributes alongside the collection.")


class HostConfigCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "host_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(HostConfigSchema()),
        description="A list of host objects.",
    )


class FolderCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "folder_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(FolderSchema()),
        description="A list of folder objects.",
    )


class DateTimeRange(BaseSchema):
    start_time = gui_fields.Timestamp(
        required=True,
        example="2017-07-21T17:32:28+00:00",
        description="The start datetime of the time period. The format conforms to the ISO 8601 profile",
    )
    end_time = gui_fields.Timestamp(
        example="2017-07-21T17:32:28+00:00",
        description="The end datetime of the time period. The format conforms to the ISO 8601 profile",
        format="iso8601",
    )


class ConcreteDisabledNotifications(BaseSchema):
    disable = fields.Boolean(
        required=False,
        description="Option if all notifications should be temporarily disabled",
    )
    timerange = fields.Nested(
        DateTimeRange,
        description="A custom timerange during which notifications are disabled",
        required=False,
    )


class ConcreteUserInterfaceAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
        example="default",
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
        example="right",
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
        example="hide",
    )
    mega_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "mega menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
        example="topic",
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
        example="default",
    )


class UserIdleOption(BaseSchema):
    option = fields.String(
        required=True,
        description="This field indicates if the idle timeout uses the global configuration, is "
        "disabled or uses an individual duration",
        enum=["global", "disable", "individual"],
    )
    duration = fields.Integer(
        required=False,
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=3600,
    )


class ConcreteUserContactOption(BaseSchema):
    email = fields.String(
        required=True,
        description="The mail address of the user.",
        example="user@example.com",
    )
    fallback_contact = fields.Boolean(
        description="In case none of the notification rules handle a certain event a notification "
        "will be sent to the specified email",
        required=False,
    )


class UserAttributes(BaseSchema):
    fullname = fields.String(required=True, description="The alias or full name of the user.")
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
    )
    disable_login = fields.Boolean(
        required=False,
        description="This field indicates if the user is allowed to login to the monitoring.",
    )
    contact_options = fields.Nested(
        ConcreteUserContactOption,
        required=False,
        description="Contact settings for the user",
    )
    idle_timeout = fields.Nested(
        UserIdleOption,
        required=False,
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
    )
    roles = fields.List(
        fields.String(),
        description="The list of assigned roles to the user",
    )
    authorized_sites = fields.List(
        fields.String(),
        description="The names of the sites that this user is authorized to handle",
        required=False,
    )
    contactgroups = fields.List(
        fields.String(),
        description="The contact groups that this user is a member of",
        required=False,
    )
    pager_address = fields.String(
        required=False,
        description="",
    )
    disable_notifications = fields.Nested(
        ConcreteDisabledNotifications,
        required=False,
    )
    language = fields.String(
        required=False,
        description="The language used by the user in the user interface",
    )
    enforce_password_change = fields.Boolean(
        required=False,
        description="This field indicates if the user is forced to change the password on the "
        "next login or access.",
    )
    interface_options = fields.Nested(
        ConcreteUserInterfaceAttributes,
        required=False,
    )


class UserObject(DomainObject):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(UserAttributes, description="The attributes of the user")


class UserCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(UserObject),
        description="A list of user objects.",
    )


TIME_FIELD = fields.String(
    example="14:00",
    format="time",
    description="The hour of the time period.",
)


class ConcreteTimeRange(BaseSchema):
    start = TIME_FIELD
    end = TIME_FIELD


class ConcreteTimeRangeActive(BaseSchema):
    day = fields.String(
        description="The day for which the time ranges are specified",
        pattern=f"{'|'.join(weekday_ids())}",
    )
    time_ranges = fields.List(fields.Nested(ConcreteTimeRange))


class ConcreteTimePeriodException(BaseSchema):
    date = fields.String(
        example="2020-01-01",
        format="date",
        description="The date of the time period exception." "8601 profile",
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
        example={"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]},
    )
    exceptions = fields.List(
        fields.Nested(ConcreteTimePeriodException),
        description="Specific day exclusions with their list of time ranges",
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}],
    )
    exclude = fields.List(  # type: ignore[assignment]
        fields.String(description="Name of excluding time period", example="holidays"),
        description="The collection of time period aliases whose periods are excluded",
    )


class PasswordExtension(BaseSchema):
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
        attribute="docu_url",
        description="The URL pointing to documentation or any other page.",
    )
    password = fields.String(
        required=True,
        example="password",
        description="The password string",
    )
    owned_by = fields.String(
        example="admin",
        description="The owner of the password who is able to edit, delete and use existing passwords.",
    )

    shared = fields.List(
        fields.String(
            example="all",
            description="The member the password is shared with",
        ),
        example=["all"],
        attribute="shared_with",
        description="The list of members the password is shared with",
    )
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
    )


class PasswordObject(DomainObject):
    domainType = fields.Constant(
        "password",
        description="The type of the domain-object.",
    )
    extensions = fields.Nested(
        PasswordExtension,
        description="All the attributes of the domain object.",
    )


class InstalledVersions(BaseSchema):
    site = fields.String(
        description="The site where this API call was made on.", example="production"
    )
    group = fields.String(
        description="The Apache WSGI application group this call was made on.", example="de"
    )
    rest_api = fields.Dict(description="The REST-API version", example={"revision": "1.0.0"})
    versions = fields.Dict(description="Some version numbers", example={"checkmk": "1.8.0p1"})
    edition = fields.String(description="The Checkmk edition.", example="raw")
    demo = fields.Boolean(description="Whether this is a demo version or not.", example=False)


class VersionCapabilities(BaseSchema):
    blobsClobs = fields.Boolean(
        required=False,
        description="attachment support",
    )
    deleteObjects = fields.Boolean(
        required=False,
        description=(
            "deletion of persisted objects through the DELETE Object resource C14.3," " see A3.5"
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


class X509PEM(BaseSchema):
    cert = fields.String(
        required=True,
        description="PEM-encoded X.509 certificate.",
    )
