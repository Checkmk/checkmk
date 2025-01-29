#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A few upgraded Fields which handle some OpenAPI validation internally."""

import ast
import json
import logging
import re
import typing
import uuid
import warnings
from collections.abc import Callable, Collection, Mapping
from datetime import datetime, timezone
from typing import Any, Literal

from cryptography.x509 import CertificateSigningRequest, load_pem_x509_csr
from cryptography.x509.oid import NameOID
from marshmallow import fields as _fields
from marshmallow import post_load, pre_dump, utils, ValidationError
from marshmallow_oneofschema import OneOfSchema

from cmk.ccc import version
from cmk.ccc.exceptions import MKException

from cmk.utils import paths
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.livestatus_helpers.expressions import NothingExpression, QueryExpression
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hostgroups, Hosts, Servicegroups
from cmk.utils.livestatus_helpers.types import Column, Table
from cmk.utils.regex import regex, REGEX_ID
from cmk.utils.tags import TagGroupID, TagID
from cmk.utils.user import UserId

from cmk.gui import sites
from cmk.gui.config import builtin_role_ids
from cmk.gui.customer import customer_api, SCOPE_GLOBAL
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.base import BaseSchema, MultiNested, ValueTypedDictSchema
from cmk.gui.fields.utils import attr_openapi_schema, ObjectContext, ObjectType, tree_to_expr
from cmk.gui.groups import GroupName, GroupType
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.site_config import configured_sites
from cmk.gui.userdb import load_users
from cmk.gui.watolib import userroles
from cmk.gui.watolib.groups_io import load_group_information
from cmk.gui.watolib.host_attributes import host_attribute
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.passwords import contact_group_choices, password_exists
from cmk.gui.watolib.sites import site_management_registry
from cmk.gui.watolib.tags import load_tag_group

from cmk.fields import base, DateTime, validators

_logger = logging.getLogger(__name__)
_CONNECTION_ID_PATTERN = "^[-a-z0-9A-Z_]+$"


class PythonString(base.String):
    """Represent a Python value expression.

    Any native Python datastructures like tuple, dict, set, etc. can be used.

        Examples:

            >>> expr = PythonString()
            >>> expr.deserialize("{}")
            {}

            >>> expr.deserialize("{'a': (5.5, None)}")
            {'a': (5.5, None)}

            >>> expr.deserialize("...")  # doctest: +ELLIPSIS
            Ellipsis

            >>> expr.deserialize("''")
            ''

            >>> expr.serialize("foo", {"foo": ""})
            "''"

        Borked syntax leads to an ValidationError

            >>> expr.deserialize("{'a': (5.5,")  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: ...

            >>> expr.deserialize("globals")  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: ...

            >>> expr.deserialize('{"foo": "bar"}["foo"]')  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            marshmallow.exceptions.ValidationError: ...

    """

    def _serialize(self, value: str, attr: object, obj: object, **kwargs: Any) -> str:
        return repr(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str):
            raise ValidationError("Unsupported type. Field must be string.")
        try:
            return ast.literal_eval(value)
        except SyntaxError as exc:
            msg = str(exc).replace(" (<unknown>, line 1)", "")
            raise ValidationError(f"Syntax Error: {msg} in {value!r}") from exc
        except ValueError as exc:
            raise ValidationError(f"Not a Python data structure: {value!r}") from exc


# NOTE
# All these non-capturing match groups are there to properly distinguish the alternatives.
FOLDER_PATTERN = r"^(?:(?:[~\\\/]|(?:[~\\\/][-_ a-zA-Z0-9.]+)+[~\\\/]?)|[0-9a-fA-F]{32})$"


class FolderField(base.String):
    """This field represents a Setup Folder.

    It will return a Folder instance, ready to use.
    """

    default_error_messages = {
        "not_found": "The folder {folder_id!r} could not be found.",
    }

    def __init__(
        self,
        pattern=FOLDER_PATTERN,
        **kwargs,
    ):
        if "description" not in kwargs:
            kwargs["description"] = "The path name of the folder."

        kwargs["description"] += (
            "\n\nPath delimiters can be either `~`, `/` or `\\`. Please use the one most "
            "appropriate for your quoting/escaping needs. A good default choice is `~`."
        )
        super().__init__(pattern=pattern, **kwargs)

    @classmethod
    def _normalize_folder(cls, folder_id):
        r"""Normalizes a folder representation

        Args:
            folder_id:
                A representation of a folder.

        Examples:

            >>> FolderField._normalize_folder("\\")
            '/'

            >>> FolderField._normalize_folder("~")
            '/'

            >>> FolderField._normalize_folder("/foo/bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("\\foo\\bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("~foo~bar")
            '/foo/bar'

            >>> FolderField._normalize_folder("/foo/bar/")
            '/foo/bar'

        Returns:
            The normalized representation.

        """
        prev = folder_id
        separators = ["\\", "~"]
        while True:
            for sep in separators:
                folder_id = folder_id.replace(sep, "/")
            if prev == folder_id:
                break
            prev = folder_id
        if len(folder_id) > 1 and folder_id.endswith("/"):
            folder_id = folder_id[:-1]
        return folder_id

    @classmethod
    def load_folder(cls, folder_id: str) -> Folder:
        def _ishexdigit(hex_string: str) -> bool:
            try:
                int(hex_string, 16)
                return True
            except ValueError:
                return False

        tree = folder_tree()
        if folder_id == "/":
            folder = tree.root_folder()
        elif _ishexdigit(folder_id):
            folder = tree._by_id(folder_id)
        else:
            folder_id = cls._normalize_folder(folder_id)
            folder = tree.folder(folder_id[1:])

        return folder

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        try:
            return self.load_folder(value)
        except MKException:
            if value:
                raise self.make_error("not_found", folder_id=value)
        return None

    def _serialize(self, value: str, attr: object, obj: object, **kwargs: Any) -> str:
        if isinstance(value, str):
            if not value.startswith("/"):
                value = f"/{value}"
            return value

        if isinstance(value, Folder):
            return "/" + value.path()

        raise ValueError(f"Unknown type: {value!r}")


class BinaryExprSchema(BaseSchema):
    """

    >>> q = {'left': 'name', 'op': '=', 'right': 'foo'}
    >>> result = BinaryExprSchema().load(q)
    >>> assert result == q

    """

    op = base.String(description="The operator.")
    left = base.String(
        description="The LiveStatus column name.", pattern=r"^([a-z]+\.)?[_a-z]+$", example="name"
    )
    right = base.String(
        description="The value to compare the column to."
    )  # should be AnyOf(all openapi types)


class NotExprSchema(BaseSchema):
    """Expression negating another query expression.

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> input_expr = {'op': '=', 'left': 'hosts.name', 'right': 'foo'}
        >>> q = {'op': 'not', 'expr': input_expr}
        >>> result = NotExprSchema(context={'table': Hosts}).load(q)
        >>> assert result == q

    """

    op = base.String(description="The operator. In this case `not`.")
    expr = base.Nested(
        lambda: ExprSchema(),
        description="The query expression to negate.",
    )


class LogicalExprSchema(BaseSchema):
    """Expression combining multiple other query expressions."""

    op = base.String(description="The operator.")
    # many=True does not work here for some reason.
    expr = base.List(
        base.Nested(
            lambda *a, **kw: ExprSchema(*a, **kw),
            description="A list of query expressions to combine.",
        )
    )


class ExprSchema(OneOfSchema):
    """Top level class for query expression schema

    Operators can be one of: AND, OR

    Examples:

        >>> q = {'op': 'and', 'expr': [
        ...         {'op': 'not', 'expr':
        ...             {'op': 'or', 'expr': [
        ...                 {'op': '=', 'left': 'name', 'right': 'foo'},
        ...                 {'op': '=', 'left': 'name', 'right': 'bar'},
        ...             ]},
        ...         },
        ...     ]}

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> schema = ExprSchema(context={'table': Hosts})
        >>> assert schema.load(q) == schema.load(json.dumps(q))

        >>> q = {'op': '=', 'left': 'foo', 'right': 'bar'}
        >>> schema.load(q)
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Table 'hosts' has no column 'foo'.

    """

    type_field = "op"
    type_field_remove = False
    type_schemas = {
        "and": LogicalExprSchema,
        "or": LogicalExprSchema,
        "not": NotExprSchema,
        "=": BinaryExprSchema,
        "~": BinaryExprSchema,
        "~~": BinaryExprSchema,
        "<": BinaryExprSchema,
        ">": BinaryExprSchema,
        ">=": BinaryExprSchema,
        "<=": BinaryExprSchema,
        "!=": BinaryExprSchema,
        "!~": BinaryExprSchema,
        "!~~": BinaryExprSchema,
        "!<": BinaryExprSchema,
        "!>": BinaryExprSchema,
        "!>=": BinaryExprSchema,
        "!<=": BinaryExprSchema,
    }

    def load(self, data, *, many=None, partial=None, unknown=None, **kwargs):
        # When being passed in via the query string, we may get the raw JSON string instead of
        # the deserialized dictionary. We need to unpack it ourselves.
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError as exc:
                raise ValidationError(
                    {
                        "_schema": [
                            f"Invalid JSON value: '{data}'",
                            str(exc),
                        ],
                    }
                )
        elif isinstance(data, QueryExpression):
            return data

        if not self.context or "table" not in self.context:
            raise RuntimeError(f"No table in context for field {self}")

        if not data:
            return NothingExpression()

        try:
            tree_to_expr(data, self.context["table"])
        except ValueError as e:
            raise ValidationError(str(e)) from e
        return super().load(data, many=many, partial=partial, unknown=unknown, **kwargs)


class _ExprNested(base.Nested):
    def _load(self, value, data, partial=None):
        _data = super()._load(value, data, partial=partial)
        return tree_to_expr(_data, table=self.metadata["table"])


def query_field(
    table: type[Table], required: bool = False, example: str | None = None
) -> base.Nested:
    """Returns a Nested ExprSchema Field which validates a Livestatus query.

    Args:
        table:
            A Livestatus Table class.
        required:
            Whether the field shall be required.
        example:
            optional query example

    Returns:
        A marshmallow Nested field.

    """

    if example is None:
        example = json.dumps(
            {
                "op": "and",
                "expr": [
                    {"op": "=", "left": "name", "right": "example.com"},
                    {"op": "!=", "left": "state", "right": "0"},
                ],
            }
        )

    return _ExprNested(
        ExprSchema(context={"table": table}),
        table=table,
        description=(
            f"An query expression of the Livestatus {table.__tablename__!r} table in nested "
            "dictionary form. If you want to use multiple expressions, nest them with the "
            "AND/OR operators."
        ),
        many=False,
        example=example,
        required=required,
    )


ColumnTypes = Column | str


def column_field(
    table: type[Table],
    example: list[str],
    required: bool = False,
    mandatory: list[ColumnTypes] | None = None,
    default: list[Column] | None = None,
) -> "_ListOfColumns":
    column_names: list[str] = []
    if mandatory is not None:
        for col in mandatory:
            if isinstance(col, Column):
                column_names.append(col.name)
            else:
                column_names.append(col)
    if default is None:
        default = [getattr(table, col) for col in column_names]

    return _ListOfColumns(
        _LiveStatusColumn(table=table, required=required),
        table=table,
        required=required,
        mandatory=column_names,
        load_default=default,
        description=f"The desired columns of the `{table.__tablename__}` table. If left empty, a "
        "default set of columns is used.",
        example=example,
    )


class _ListOfColumns(base.List):
    """Manages a list of Livestatus columns and returns Column instances

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> cols = _ListOfColumns(
        ...     _LiveStatusColumn(table=Hosts),
        ...     table=Hosts,
        ... )
        >>> cols.deserialize(['name', 'alias'])
        [Column(hosts.name: string), Column(hosts.alias: string)]

        >>> cols = _ListOfColumns(
        ...     _LiveStatusColumn(table=Hosts),
        ...     table=Hosts,
        ...     mandatory=[Hosts.name],
        ... )
        >>> cols.deserialize(['alias'])
        [Column(hosts.name: string), Column(hosts.alias: string)]

        >>> class FooSchema(BaseSchema):
        ...      columns = _ListOfColumns(
        ...          _LiveStatusColumn(table=Hosts),
        ...          table=Hosts,
        ...          mandatory=[Hosts.name])
        >>> schema = FooSchema()
        >>> schema.load({'columns': ['alias']})
        {'columns': [Column(hosts.name: string), Column(hosts.alias: string)]}

    """

    default_error_messages = {
        "unknown_column": "Unknown default column: {table_name}.{column_name}",
    }

    def __init__(
        self,
        cls_or_instance: _fields.Field | type,
        table: type[Table],
        mandatory: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(cls_or_instance, **kwargs)
        self.table = table
        self.mandatory = mandatory if mandatory is not None else []
        for column in self.mandatory:
            if column not in table.__columns__():
                raise ValueError(
                    f"Column {column!r} in parameter 'mandatory' is not a column "
                    f"of table {table.__tablename__!r}"
                )

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data)
        for column in reversed(self.mandatory):
            if isinstance(column, Column):
                column_name = column.name
            else:
                column_name = column
            if column_name not in value:
                value.insert(0, column_name)
        return [getattr(self.table, col) for col in value]


class _LiveStatusColumn(base.String):
    """Represents a LiveStatus column.

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> _LiveStatusColumn(table=Hosts).deserialize('name')
        'name'

        >>> _LiveStatusColumn(table=Hosts).deserialize('bar')
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unknown column: hosts.bar
    """

    default_error_messages = {
        "unknown_column": "Unknown column: {table_name}.{column_name}",
    }

    def _deserialize(self, value, attr, data, **kwargs):
        table = self.metadata["table"]
        if value not in table.__columns__():
            raise self.make_error(
                "unknown_column", table_name=table.__tablename__, column_name=value
            )
        return value


HOST_NAME_REGEXP = r"^[-0-9a-zA-Z_.]+\Z"


class HostField(base.String):
    """A field representing a hostname."""

    default_error_messages = {
        "should_exist": "Host not found: {host_name!r}",
        "should_not_exist": "Host {host_name!r} already exists.",
        "should_be_monitored": "Host {host_name!r} should be monitored but it's not. "
        "Activate the configuration?",
        "should_not_be_monitored": "Host {host_name!r} should not be monitored but it is. "
        "Activate the configuration?",
        "should_be_cluster": "Host {host_name!r} is not a cluster host, but needs to be.",
        "should_not_be_cluster": "Host {host_name!r} may not be a cluster host, but is.",
        "pattern": "{value!r} does not match pattern {pattern!r}.",
        "invalid_name": "The provided name for host {host_name!r} is invalid: {invalid_reason!r}",
    }

    def __init__(
        self,
        example: str = "example.com",
        pattern: str = HOST_NAME_REGEXP,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        should_exist: bool | None = True,
        should_be_monitored: bool | None = None,
        should_be_cluster: bool | None = None,
        skip_validation_on_view: bool = False,
        permission_type: Literal["setup_write", "setup_read", "monitor"] = "monitor",
        **kwargs: Any,
    ) -> None:
        if not should_exist and should_be_cluster is not None:
            raise ValueError("Can't be missing and checking for cluster status!")

        self._should_exist = should_exist
        self._should_be_monitored = should_be_monitored
        self._should_be_cluster = should_be_cluster
        self._skip_validation_on_view = skip_validation_on_view
        self._permission_type = permission_type
        super().__init__(
            example=example,
            pattern=pattern,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _confirm_user_has_permission(self, host: Host | None) -> None:
        if self._permission_type == "monitor":
            return

        if host:
            host._user_needs_permission("read")
            if self._permission_type == "setup_write":
                host._user_needs_permission("write")

        return

    def _deserialize(
        self,
        value: Any,
        attr: str | None,
        data: typing.Mapping[str, Any] | None,
        **kwargs: Any,
    ) -> HostAddress:
        value = super()._deserialize(value, attr, data, **kwargs)
        try:
            return HostAddress(value)
        except ValueError as e:
            raise ValidationError(str(e)) from e

    def _validate(self, value):
        super()._validate(value)
        host = Host.host(value)
        self._confirm_user_has_permission(host)

        if (
            self._skip_validation_on_view
            and self.context is not None
            and self.context.get("object_context") == "view"
        ):
            return

        # Regex gets checked through the `pattern` of the String instance

        if self._should_exist is not None:
            if self._should_exist and host is None:
                raise self.make_error("should_exist", host_name=value)

            if not self._should_exist and host is not None:
                raise self.make_error("should_not_exist", host_name=value)

        if self._should_be_cluster is not None:
            if host is None:
                raise self.make_error("should_exist", host_name=value)

            if self._should_be_cluster and not host.is_cluster():
                raise self.make_error("should_be_cluster", host_name=value)

            if not self._should_be_cluster and host.is_cluster():
                raise self.make_error("should_not_be_cluster", host_name=value)

        if self._should_be_monitored is not None:
            monitored = host_is_monitored(value)
            if self._should_be_monitored and not monitored:
                raise self.make_error("should_be_monitored", host_name=value)

            if not self._should_be_monitored and monitored:
                raise self.make_error("should_not_be_monitored", host_name=value)


def group_is_monitored(group_type, group_name):
    # Danke mypy
    rv: bool
    if group_type == "service":
        rv = bool(
            Query([Servicegroups.name], Servicegroups.name == group_name).first_value(sites.live())
        )
    elif group_type == "host":
        rv = bool(Query([Hostgroups.name], Hostgroups.name == group_name).first_value(sites.live()))
    else:
        raise ValueError("Unknown group type.")
    return rv


def host_is_monitored(host_name: str) -> bool:
    return bool(Query([Hosts.name], Hosts.name == host_name).first_value(sites.live()))


def validate_custom_host_attributes(
    host_attributes: dict[str, str],
    errors: typing.Literal["warn", "raise"],
) -> dict[str, str]:
    """Validate only custom host attributes

    Args:
        host_attributes:
            The host attributes a dictionary with the attributes as keys (without any prefixes)
            and the values as values.

        errors:
            Either `warn` or `raise`. When set to `warn`, errors will just be logged, when set to
            `raise`, errors will lead to a ValidationError being raised.

    Returns:
        The data unchanged.

    Raises:
        ValidationError: when `errors` is set to `raise`

    """
    for name, value in host_attributes.items():
        try:
            attribute = host_attribute(name)
        except KeyError as exc:
            if errors == "raise":
                raise ValidationError(
                    {name: f"No such attribute, {name!r}"}, field_name=name
                ) from exc

            _logger.error("No such attribute: %s", name)
            return host_attributes

        try:
            attribute.validate_input(value, "")
        except MKUserError as exc:
            if errors == "raise":
                raise ValidationError({name: str(exc)}) from exc

            _logger.error("Error validating %s: %s", name, str(exc))

    return host_attributes


def ensure_string(value):
    if not isinstance(value, str):
        raise ValidationError(f"Not a string, but a {type(value).__name__}")


class HostnameOrIP(base.String):
    default_error_messages = {
        "too_short": "The length of {value!r} is less than the minimum {min!r}.",
        "too_long": "The length of {value!r} is more than the maximum {max!r}.",
        "should_exist": "Host not found: {host_name!r}",
        "should_not_exist": "Host {host_name!r} already exists.",
        "should_be_cluster": "Host {host_name!r} is not a cluster host, but needs to be.",
        "should_not_be_cluster": "Host {host_name!r} may not be a cluster host, but is.",
        "should_be_monitored": "Host {host_name!r} exists, but is not monitored.",
        "should_not_be_monitored": "Host {host_name!r} exists, but should not be monitored.",
    }

    def __init__(
        self,
        description: str = "A host name or IP address",
        example: str = "example.com",
        required: bool = True,
        strip: bool = True,
        minlen: int = 1,
        maxlen: int | None = None,
        host_type_allowed: Literal[
            "hostname_and_ipv4", "hostname_and_ipv6", "hostname_only", "ipv4", "ipv6"
        ] = "hostname_and_ipv4",
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        should_be_monitored: bool = False,
        should_be_cluster: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(description=description, example=example, required=required, **kwargs)

        self.strip = strip
        self.minlen = minlen
        self.maxlen = maxlen
        self.host_type_allowed = host_type_allowed
        self.presence = presence
        self.should_be_monitored = should_be_monitored
        self.should_be_cluster = should_be_cluster

    def _validate(self, value: str) -> None:
        if self.strip:
            value = value.strip()

        super()._validate(value)

        validate_results: dict[str, ValidationError | Literal["pass"]] = {
            "hostname": self._validate_hostname(value),
            "ipv4": self._validate_ip4(value),
            "ipv6": self._validate_ip6(value),
        }

        validated_host_type_names = {k for k, v in validate_results.items() if v == "pass"}

        match self.host_type_allowed:
            case "hostname_and_ipv4":
                if validated_host_type_names.difference({"ipv4", "hostname"}):
                    self._raise_an_error(validate_results)

            case "hostname_and_ipv6":
                if validated_host_type_names.difference({"ipv6", "hostname"}):
                    self._raise_an_error(validate_results)

            case "hostname_only":
                if validated_host_type_names.difference({"hostname"}):
                    self._raise_an_error(validate_results)

            case "ipv4":
                if "ipv4" not in validated_host_type_names:
                    self._raise_an_error(validate_results)

            case "ipv6":
                if "ipv6" not in validated_host_type_names:
                    self._raise_an_error(validate_results)

        if len(value) < self.minlen:
            self.make_error("too_short", value=value, min=self.minlen)

        if self.maxlen:
            if len(value) > self.maxlen:
                self.make_error("too_long", value=value, min=self.minlen)

    def _raise_an_error(
        self, validate_results: Mapping[str, ValidationError | Literal["pass"]]
    ) -> None:
        for val_error in {v for _, v in validate_results.items() if v != "pass"}:
            raise val_error

    def _validate_hostname(self, value: str) -> ValidationError | Literal["pass"]:
        try:
            if self.presence != "ignore" or self.should_be_cluster or self.should_be_monitored:
                if host := Host.host(HostName(value)):
                    if self.presence == "should_not_exist":
                        raise self.make_error("should_not_exist", host_name=value)

                    if self.should_be_cluster and not host.is_cluster():
                        raise self.make_error("should_be_cluster", host_name=value)

                    if not self.should_be_cluster and host.is_cluster():
                        raise self.make_error("should_not_be_cluster", host_name=value)

                    if self.should_be_monitored and not host_is_monitored(value):
                        raise self.make_error("should_be_monitored", host_name=value)

                    if not self.should_be_monitored and host_is_monitored(value):
                        raise self.make_error("should_not_be_monitored", host_name=value)
                else:
                    raise self.make_error("should_exist", host_name=value)

            if not re.match("^(:?" + HOST_NAME_REGEXP + ")$", value):
                raise self.make_error("pattern", value=value, pattern=HOST_NAME_REGEXP)

        except ValidationError as ve:
            return ve
        return "pass"

    def _validate_ip4(self, value: str) -> ValidationError | Literal["pass"]:
        try:
            validators.ValidateIPv4()(value)
        except ValidationError as ve:
            return ve
        return "pass"

    def _validate_ip6(self, value: str) -> ValidationError | Literal["pass"]:
        try:
            validators.ValidateIPv6()(value)
        except ValidationError as ve:
            return ve
        return "pass"


class CustomHostAttributes(ValueTypedDictSchema):
    value_type = ValueTypedDictSchema.field(
        base.String(
            description="Each tag is a mapping of string to string",
            validate=ensure_string,
        )
    )

    @post_load
    def _valid(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        # NOTE
        # If an attribute gets deleted AFTER it has already been set to a host or a folder,
        # then this would break here. We therefore can't validate outbound data as thoroughly
        # because our own data can be inherently inconsistent.
        if self.context["direction"] == "outbound":
            return validate_custom_host_attributes(data, "warn")
        else:
            return validate_custom_host_attributes(data, "raise")


class TagGroupAttributes(ValueTypedDictSchema):
    """Schema to validate tag groups

    Examples:
        >>> schema = TagGroupAttributes()
        >>> schema.load({"foo": "bar"})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'foo': "Tag group name must start with 'tag_'"}

        >>> schema.load({"tag_foo": "bar"})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'tag_foo': 'No such tag-group.'}

        >>> schema.load({"tag_agent": "flint"})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'tag_agent': "Invalid value for tag-group: 'flint'"}

        >>> schema.load({"tag_agent": "cmk-agent"})
        {'tag_agent': 'cmk-agent'}

        >>> schema.dump({"tag_agent": "cmk-agent"})
        {'tag_agent': 'cmk-agent'}

        >>> schema.load({"tag_agent": None})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'tag_agent': 'Invalid value for tag-group: None'}

        >>> schema.dump({"tag_agent": None})
        {'tag_agent': None}

    """

    value_type = ValueTypedDictSchema.field(
        base.String(
            description=(
                "The value of the tag-group attribute. Each tag is a mapping of string to string, "
                "where the tag name must start with `tag_`."
            ),
            allow_none=True,
        )
    )

    def _validate_tag_group(self, name: str) -> set[TagID | None]:
        if not name.startswith("tag_"):
            raise ValidationError({name: "Tag group name must start with 'tag_'"})

        try:
            tag_group = load_tag_group(TagGroupID(name[4:]))
        except MKUserError as exc:
            raise ValidationError({name: str(exc)}) from exc

        if tag_group is None:
            raise ValidationError({name: "No such tag-group."})

        # FIXME: This should eventually be moved into TagGroup

        # Checkbox tags are allowed to have no value at all. This means they are deactivated.
        allowed_ids = tag_group.get_tag_ids()
        if tag_group.is_checkbox_tag_group:
            allowed_ids.add(None)

        return allowed_ids

    @pre_dump
    def _pre_dump(self, data: dict[str, str], **kwargs: Any) -> dict[str, str]:
        rv: dict[str, str] = {}
        for key, value in data.items():
            allowed_ids = self._validate_tag_group(key)

            if value not in allowed_ids:
                warnings.warn(f"Invalid value for tag-group {key}: {value!r}")

            rv[key] = value

        return rv

    @post_load
    def _post_load(self, data: dict[str, str], **kwargs: Any) -> dict[str, str]:
        rv: dict[str, str] = {}
        for key, value in data.items():
            allowed_ids = self._validate_tag_group(key)

            if value not in allowed_ids:
                raise ValidationError({key: f"Invalid value for tag-group: {value!r}"})

            rv[key] = value

        return rv


def host_attributes_field(
    object_type: ObjectType,
    object_context: ObjectContext,
    direction: typing.Literal["inbound", "outbound"],
    description: str | None = None,
    example: Any | None = None,
    required: bool = False,
    load_default: Any = utils.missing,
    many: bool = False,
) -> _fields.Field:
    """Build an Attribute Field

    Args:
        object_type:
            May be one of 'folder', 'host' or 'cluster'.

        object_context:
            May be 'create', 'update' or 'view'. Deletion is considered as 'update'.

        direction:
            If the data is *coming from* the user (inbound) or *going to* the user (outbound).

        description:
            A descriptive text of this field. Required.

        example:
            An example for the OpenAPI documentation. Required.

        required:
            Whether the field must be sent by the client or is option.

        load_default:
        many:

    Returns:

    """
    if description is None:
        # SPEC won't validate without description, though the error message is very obscure, so we
        # clarify this here by force.
        raise ValueError("description is necessary.")

    return MultiNested(
        [
            lambda: attr_openapi_schema(object_type, object_context),
            CustomHostAttributes,
            TagGroupAttributes,
        ],
        metadata={"context": {"object_context": object_context, "direction": direction}},
        merged=True,  # to unify both models
        description=description,
        example=example,
        many=many,
        load_default=dict if load_default is utils.missing else utils.missing,
        required=required,
    )


class SiteField(base.String):
    """A field representing a site name."""

    default_error_messages = {
        "should_exist": "The site {site!r} should exist but it doesn't.",
        "should_not_exist": "The site {site!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist", "should_not_exist", "might_not_exist_on_view", "ignore"
        ] = "should_exist",
        allow_all_value: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.presence = presence
        self.allow_all_value = allow_all_value

    def _validate(self, value):
        if self.allow_all_value and value == "all":
            return

        if (
            self.presence == "might_not_exist_on_view"
            and self.context is not None
            and self.context["object_context"] == "view"
        ):
            return

        if self.presence in ["should_exist", "might_not_exist_on_view"]:
            if value not in configured_sites().keys():
                raise self.make_error("should_exist", site=value)

        if self.presence == "should_not_exist":
            if value in configured_sites().keys():
                raise self.make_error("should_not_exist", site=value)

    def _serialize(self, value, attr, obj, **kwargs):
        if self.presence == "might_not_exist_on_view" and value not in configured_sites().keys():
            return "Unknown Site: " + value
        return super()._serialize(value, attr, obj, **kwargs)


class _CustomerField(base.String):
    """A field representing a customer"""

    default_error_messages = {
        "invalid_global": "Invalid customer: global",
        "should_exist": "Customer missing: {customer!r}",
        "should_not_exist": "Customer {customer!r} already exists.",
    }

    def __init__(
        self,
        example: str = "provider",
        description: str = "By specifying a customer, you configure on which sites the user object will be "
        "available. 'global' will make the object available on all sites.",
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        allow_global: bool = True,
        should_exist: bool = True,
        **kwargs: Any,
    ):
        self._should_exist = should_exist
        self._allow_global = allow_global
        super().__init__(
            example=example,
            description=description,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        if value == "global":
            value = SCOPE_GLOBAL

        if not self._allow_global and value is None:
            raise self.make_error("invalid_global")

        included = value in customer_api().customer_collection()
        if self._should_exist and not included:
            raise self.make_error("should_exist", customer=value)
        if not self._should_exist and included:
            raise self.make_error("should_not_exist", customer=value)

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return None if value == "global" else value


def customer_field(**kw: Any) -> _CustomerField | None:
    if version.edition(paths.omd_root) is version.Edition.CME:
        return _CustomerField(**kw)
    return None


def customer_field_response(**kw: Any) -> _CustomerField | None:
    if "description" not in kw:
        kw["description"] = "The customer for which the object is configured."
    return customer_field(**kw)


def verify_group_exists(group_type: GroupType, name: GroupName) -> bool:
    specific_existing_groups = load_group_information()[group_type]
    return name in specific_existing_groups


class GroupField(base.String):
    """A field representing a group."""

    default_error_messages = {
        "should_exist": "Group missing: {name!r}",
        "should_not_exist": "Group {name!r} already exists.",
        "should_be_monitored": "Group {host_name!r} exists, but is not monitored. "
        "Activate the configuration?",
        "should_not_be_monitored": "Group {host_name!r} exists, but should not be monitored. "
        "Activate the configuration?",
        "invalid_name": "The provided name {name!r} is invalid",
    }

    def __init__(
        self,
        group_type: Literal["host", "service", "contact"],
        example: str,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        should_exist: bool = True,
        should_be_monitored: bool | None = None,
        **kwargs: Any,
    ):
        self._group_type = group_type
        self._should_exist = should_exist
        self._should_be_monitored = should_be_monitored
        if should_be_monitored and not should_exist:
            raise ValueError("No use in trying to validate deleted but still monitored groups.")

        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        group_exists = verify_group_exists(self._group_type, value)
        if self._should_exist and not group_exists:
            raise self.make_error("should_exist", name=value)

        if not self._should_exist and group_exists:
            raise self.make_error("should_not_exist", name=value)

        if self._should_be_monitored is not None:
            monitored = group_is_monitored(self._group_type, value)
            if self._should_be_monitored and not monitored:
                raise self.make_error("should_be_monitored", host_name=value)

            if not self._should_be_monitored and monitored:
                raise self.make_error("should_not_be_monitored", host_name=value)


class PasswordIdent(base.String):
    """A field representing a password identifier"""

    default_error_messages = {
        "pattern": "{name!r} does not match pattern. An identifier must only consist of letters, digits, dash and underscore and it must start with a letter or underscore.",
        "should_exist": "Identifier missing: {name!r}",
        "should_not_exist": "Identifier {name!r} already exists.",
        "contains_colon": "Identifier {name!r} contains a colon.",
    }

    def __init__(
        self,
        example: str,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        should_exist: bool = True,
        **kwargs: Any,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value: str) -> None:
        super()._validate(value)

        pattern: re.Pattern[str] = regex(REGEX_ID, re.ASCII)
        if pattern.match(value) is None:
            raise self.make_error("pattern", name=value)

        exists = password_exists(value)
        if self._should_exist and not exists:
            raise self.make_error("should_exist", name=value)

        if not self._should_exist and exists:
            raise self.make_error("should_not_exist", name=value)


class PasswordEditableBy(base.String):
    """A field representing which group can edit a password"""

    default_error_messages = {
        "invalid": "Specified contact group does not exist or you do not have the necessary permissions: {name!r}",
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        """Verify if the specified editor is valid for the logged-in user

        Non-admin users cannot specify admin as the editor
        """
        super()._validate(value)
        if user.may("wato.edit_all_passwords"):
            permitted_group_ids = [group[0] for group in contact_group_choices(only_own=False)]
            permitted_group_ids.append("admin")
        else:
            permitted_group_ids = [group[0] for group in contact_group_choices(only_own=True)]

        if value not in permitted_group_ids:
            raise self.make_error("invalid", name=value)


class PasswordShare(base.String):
    """A field representing a password share group"""

    default_error_messages = {
        "invalid": "The password cannot be shared with specified group: {name!r}",
    }

    def __init__(
        self,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        shareable_groups = [group[0] for group in contact_group_choices()]
        if value not in ["all", *shareable_groups]:
            raise self.make_error("invalid", name=value)


def from_timestamp(value: float) -> datetime:
    return datetime.fromtimestamp(value, tz=timezone.utc)


def to_timestamp(value: datetime) -> float:
    return float(datetime.timestamp(value))


class Timestamp(DateTime):
    """A timestamp field for Checkmk timestamp

    Examples:

        >>> from marshmallow import Schema
        >>> class TestSchema(Schema):
        ...      ts_field = Timestamp()

        >>> value = {'ts_field': 0.0}

        >>> schema = TestSchema()
        >>> schema.dump({'ts_field': '0.0'})
        {'ts_field': '1970-01-01T00:00:00+00:00'}

        >>> schema.dump({'ts_field': 1622620683.60371})
        {'ts_field': '2021-06-02T07:58:03.603710+00:00'}

        >>> dumped = schema.dump(value)
        >>> dumped
        {'ts_field': '1970-01-01T00:00:00+00:00'}

        >>> loaded = schema.load(dumped)
        >>> loaded
        {'ts_field': 0.0}

        >>> assert loaded == value, f"{loaded!r} != {value!r}"

        >>> schema.load({'ts_field': 'foo'})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: ...

    """

    OBJ_TYPE = "timestamp"

    default_error_messages = {"invalid": "Not a valid timestamp: {input!r}"}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        dt_obj = from_timestamp(float(value))
        return super()._serialize(dt_obj, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        val = super()._deserialize(value, attr, data, **kwargs)
        return datetime.timestamp(val)


class X509ReqPEMFieldUUID(base.String):
    default_error_messages = {
        "malformed": "Malformed CSR",
        "invalid": "Invalid CSR (signature and public key do not match)",
        "no_cn": "CN is missing",
        "cn_no_uuid": "CN {cn} is no valid version-4 UUID",
    }

    def _validate(self, value: CertificateSigningRequest) -> None:
        if not value.is_signature_valid:
            raise self.make_error("invalid")
        try:
            cn = value.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if isinstance(cn, bytes):
                cn = cn.decode()
        except IndexError:
            raise self.make_error("no_cn")
        try:
            uuid.UUID(
                cn,
                version=4,
            )
        except ValueError:
            raise self.make_error("cn_no_uuid", cn=cn)

    def _deserialize(
        self, value: object, attr: object, data: object, **kwargs: Any
    ) -> CertificateSigningRequest:
        try:
            return load_pem_x509_csr(
                super()
                ._deserialize(
                    value,
                    attr,
                    data,
                    **kwargs,
                )
                .encode()
            )
        except ValueError:
            raise self.make_error("malformed")


class UserRoleID(base.String):
    default_error_messages = {
        "should_not_exist": "The role should not exist but it does: {role!r}",
        "should_exist": "The role should exist but it doesn't: {role!r}",
        "should_be_custom": "The role should be a custom role but it's not: {role!r}",
        "should_be_builtin": "The role should be a builtin role but it's not: {role!r}",
    }

    def __init__(
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        userrole_type: Literal["should_be_custom", "should_be_builtin", "ignore"] = "ignore",
        required: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, **kwargs)
        self.presence = presence
        self.userrole_type = userrole_type

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.presence == "should_not_exist":
            if userroles.role_exists(userroles.RoleID(value)):
                raise self.make_error("should_not_exist", role=value)

        elif self.presence == "should_exist":
            if not userroles.role_exists(userroles.RoleID(value)):
                raise self.make_error("should_exist", role=value)

        if self.userrole_type == "should_be_builtin":
            if value not in builtin_role_ids:
                raise self.make_error("should_be_builtin", role=value)

        elif self.userrole_type == "should_be_custom":
            if value in builtin_role_ids:
                raise self.make_error("should_be_custom", role=value)


class PermissionField(base.String):
    default_error_messages = {
        "invalid_permission": "The specified permission name doesn't exist: {value!r}",
    }

    def __init__(
        self,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            example="general.edit_profile",
            description="The name of a permission",
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value: str) -> None:
        super()._validate(value)
        if value not in permission_registry:
            raise self.make_error("invalid_permission", value=value)


class Username(base.String):
    default_error_messages = {
        "should_exist": "Username missing: {username!r}",
        "should_not_exist": "Username {username!r} already exists",
        "invalid_name": "Username {username!r} is not a valid checkmk username",
    }

    def __init__(
        self,
        example: str,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        should_exist: bool = True,
        **kwargs: Any,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        user.need_permission("wato.users")

        try:
            UserId(value)
        except ValueError:
            raise self.make_error("invalid_name", username=value)

        # TODO: change to names list only
        usernames = load_users()
        if self._should_exist and value not in usernames:
            raise self.make_error("should_exist", username=value)
        if not self._should_exist and value in usernames:
            raise self.make_error("should_not_exist", username=value)


class ConnectionIdentifier(base.String):
    default_error_messages = {
        "should_exist": "ConnectionId missing: {connection_id!r}",
        "should_not_exist": "ConnectionId {connection_id!r} already exists",
        "invalid_name": "ConnectionId {connection_id!r} is not a valid checkmk ConnectionId",
    }

    def __init__(
        self,
        example: str,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        **kwargs: Any,
    ):
        self._presence = presence
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            pattern=_CONNECTION_ID_PATTERN,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)
        user.need_permission("wato.sites")

        site_mgmt = site_management_registry["site_management"]
        exists = site_mgmt.broker_connection_id_exists(value)
        if self._presence == "should_exist" and not exists:
            raise self.make_error("should_exist", connection_id=value)
        if self._presence == "should_not_exist" and exists:
            raise self.make_error("should_not_exist", connection_id=value)


class FolderIDField(FolderField):
    """This field represents a folder's path.

    On deserialize, it will also check if the folder exists and will return
    the path with format 'path/to/folder' or in the case of the main folder,
    it will return ''.

    e.g.
    'path~to~folder' -> 'path/to/folder
    '~' -> ''

    On serialize, it will take the folder path str and replace all / for
    a ~. The root folder will be returned as '~'.

    e.g.
    'path/to/folder' -> 'path~to~folder
    '' -> '~'

    """

    default_error_messages = {
        "should_exist": "The folder id {folder_id!r} should exist but it doesn't.",
        "should_not_exist": "The folder id {folder_id!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.presence = presence

    def _deserialize(self, value: str, attr: object, data: object, **kwargs: Any) -> str | None:
        folder: Folder | None = None
        try:
            folder = super()._deserialize(value, attr, data)
        except ValidationError:
            if self.presence == "should_exist":
                raise self.make_error("should_exist", folder_id=value)

        if self.presence == "should_not_exist" and folder is not None:
            raise self.make_error("should_not_exist", folder_id=value)

        if folder is None:
            return None

        return folder.path()

    def _serialize(self, value: str, attr: object, obj: object, **kwargs: Any) -> str:
        folder_path = super()._serialize(value, attr, obj, **kwargs)
        return folder_path.replace("/", "~")


__all__ = [
    "host_attributes_field",
    "column_field",
    "customer_field",
    "customer_field_response",
    "DateTime",
    "ExprSchema",
    "FolderField",
    "FolderIDField",
    "FOLDER_PATTERN",
    "GroupField",
    "HostField",
    "HostnameOrIP",
    "MultiNested",
    "PasswordEditableBy",
    "PasswordIdent",
    "PasswordShare",
    "PermissionField",
    "PythonString",
    "query_field",
    "SiteField",
    "Timestamp",
    "Username",
    "UserRoleID",
    "X509ReqPEMFieldUUID",
]
