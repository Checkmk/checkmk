#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
import logging
from typing import Any

import marshmallow
from marshmallow import fields as _fields
from marshmallow import post_load, Schema
from marshmallow_oneofschema import OneOfSchema

import cmk.gui.userdb as userdb
from cmk.gui import fields as gui_fields
from cmk.gui.agent_registration import CONNECTION_MODE_FIELD
from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.base import MultiNested, ValueTypedDictSchema
from cmk.gui.fields.definitions import ensure_string
from cmk.gui.fields.utils import attr_openapi_schema, BaseSchema

from cmk import fields
from cmk.fields import base

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


class HostExtensionsEffectiveAttributesSchema(attr_openapi_schema("host", "view")):  # type: ignore
    @marshmallow.post_dump(pass_original=True)
    def add_tags_and_custom_attributes_back(
        self, dump_data: dict[str, Any], original_data: dict[str, Any], **_kwargs: Any
    ) -> dict[str, Any]:
        # Custom attributes and tags are thrown away during validation as they have no field in the schema.
        # So we dump them back in here.
        original_data.update(dump_data)
        return original_data


class HostExtensions(BaseSchema):
    folder = gui_fields.FolderField(
        description="The folder, in which this host resides.",
    )
    attributes = gui_fields.host_attributes_field(
        "host",
        "view",
        "outbound",
        description="Attributes of this host.",
        example={"ipaddress": "192.168.0.123"},
    )
    effective_attributes = fields.Nested(
        HostExtensionsEffectiveAttributesSchema(),
        required=False,
        description="All attributes of this host and all parent folders.",
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
    attributes = gui_fields.host_attributes_field(
        "folder",
        "view",
        "outbound",
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
        pattern="^[a-fA-F0-9]{32}$|root",
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


class HostTag(BaseSchema):
    id = fields.String(description="The unique identifier of this host tag", allow_none=True)
    title = fields.String(description="The title of this host tag")
    aux_tags = fields.List(fields.String(), description="The auxiliary tags this tag included in.")


class HostTagExtensions(BaseSchema):
    topic = fields.String(description="The topic this host tag group is organized in.")
    tags = fields.List(fields.Nested(HostTag()), description="The list of tags in this group.")


class ConcreteHostTagGroup(DomainObject):
    domainType = fields.Constant(
        "host_tag_group",
        required=True,
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        HostTagExtensions(), description="Additional fields for objects of this type."
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


class HostTagGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "host_tag_group",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ConcreteHostTagGroup()),
        description="A list of host tag group objects.",
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


class DiscoveryBackgroundJobStatusObject(DomainObject):
    domainType = fields.Constant(
        "discovery_run",
        description="The domain type of the object",
    )
    extensions = fields.Nested(
        BackgroundJobStatus, description="The attributes of the background job"
    )


class AuthOption(BaseSchema):
    auth_type = fields.String(
        required=False, example="password", enum=["password", "automation", "saml2", "ldap"]
    )
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
    )


class BaseUserAttributes(BaseSchema):
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
    temperature_unit = fields.String(
        required=False,
        description="The temperature unit used for graphs and perfometers.",
    )
    auth_option = fields.Nested(
        AuthOption,
        required=False,
        description="Enforce password change attribute for the user",
        example={"auth_type": "password", "enforce_password_change": False},
    )
    interface_options = fields.Nested(
        ConcreteUserInterfaceAttributes,
        required=False,
    )


class CustomUserAttributes(ValueTypedDictSchema):
    value_type = ValueTypedDictSchema.field(
        base.String(description="Each tag is a mapping of string to string", validate=ensure_string)
    )

    @post_load
    def _valid(self, user_attributes: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        # NOTE
        # If an attribute gets deleted AFTER it has already been set,
        # this would break here. We therefore can't validate outbound data as thoroughly
        # because our own data can be inherently inconsistent.

        # use the user_attribute_registry directly?
        db_user_attributes = dict(userdb.get_user_attributes())
        for name, value in user_attributes.items():
            try:
                attribute = db_user_attributes[name].valuespec()
            except KeyError:
                _logger.error("No such attribute: %s", name)
                return user_attributes

            try:
                attribute.validate_value(value, f"ua_{name}")
            except MKUserError as exc:
                _logger.error("Error validating %s: %s", name, str(exc))

        return user_attributes


def user_attributes_field(
    description: str | None = None, example: Any | None = None
) -> _fields.Field:
    """Build an Attribute Field

    Args:
        direction:
            If the data is *coming from* the user (inbound) or *going to* the user (outbound).

        description:
            A descriptive text of this field. Required.

        example:
            An example for the OpenAPI documentation. Required.
    """
    if description is None:
        # SPEC won't validate without description, though the error message is very obscure, so we
        # clarify this here by force.
        raise ValueError("description is necessary.")

    return MultiNested(
        [BaseUserAttributes, CustomUserAttributes],
        merged=True,  # to unify both models
        description=description,
        example=example,
        many=False,
        load_default=dict,
        required=False,
    )


class UserObject(DomainObject):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the object.",
    )
    extensions = user_attributes_field(
        description="The attributes of the user",
        example={"fullname": "John Doe"},
    )


class UserCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(UserObject),
        description="A list of user objects.",
    )


class UserRoleAttributes(BaseSchema):
    alias = fields.String(required=True, description="The alias of the user role.")
    permissions = fields.List(
        fields.String(),
        required=True,
        description="A list of permissions for the user role. ",
    )
    builtin = fields.Boolean(
        required=True,
        description="True if it's a builtin user role, otherwise False.",
    )
    basedon = fields.String(
        enum=builtin_role_ids,
        required=False,
        description="The builtin user role id that the user role is based on.",
    )


class UserRoleObject(DomainObject):
    domainType = fields.Constant(
        "user_role",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(UserRoleAttributes, description="All the attributes of a user role.")


class UserRoleCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "user_role",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(UserRoleObject),
        description="A list of user role objects.",
    )


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


class ConnectionMode(BaseSchema):
    connection_mode = CONNECTION_MODE_FIELD


class X509PEM(BaseSchema):
    cert = fields.String(
        required=True,
        description="PEM-encoded X.509 certificate.",
    )


class HostConfigSchemaInternal(BaseSchema):
    site = fields.String(
        required=True,
        description="The site the host is monitored on.",
    )
    is_cluster = fields.Boolean(
        required=True,
        description="Indicates if the host is a cluster host.",
    )


class AgentControllerCertificateSettings(BaseSchema):
    lifetime_in_months = fields.Integer(
        description="Lifetime of agent controller certificates in months",
        required=True,
        example=60,
    )


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


class ContactGroupObject(DomainObject):
    domainType = fields.Constant(
        "contact_group_config",
        description="The domain type of the object.",
    )


class ContactGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "contact_group_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ContactGroupObject),
        description="A list of contact group objects.",
    )


class HostGroupObject(DomainObject):
    domainType = fields.Constant(
        "host_group_config",
        description="The domain type of the object.",
    )


class HostGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "host_group_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(HostGroupObject),
        description="A list of host group objects.",
    )


class ServiceGroupObject(DomainObject):
    domainType = fields.Constant(
        "service_group_config",
        description="The domain type of the object.",
    )


class ServiceGroupCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "service_group_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ServiceGroupObject),
        description="A list of service group objects.",
    )
