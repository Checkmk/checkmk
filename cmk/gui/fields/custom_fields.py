#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from os import path
from typing import Any, Literal

from marshmallow import validate, ValidationError

from cmk.utils.tags import BuiltinTagConfig, TagID

from cmk.gui.config import active_config
from cmk.gui.groups import load_contact_group_information
from cmk.gui.plugins.userdb import utils
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.tags import (
    load_all_tag_config_read_only,
    load_tag_config_read_only,
    tag_group_exists,
)
from cmk.gui.watolib.timeperiods import verify_timeperiod_name_exists

from cmk import fields
from cmk.fields import validators


class RelativeUrl(fields.String):
    """A field representing a URL or part of a URL.

    Examples:
        >>> url_prefix = RelativeUrl(
        ...     required=False,
        ...     must_endwith_one=["/"],
        ...     example="/remote_1/",
        ...     )

        >>> url_of_remote_site = RelativeUrl(
        ...     must_startwith_one=["https", "http"],
        ...     must_endwith_one=["/check_mk/"],
        ...     required=True,
        ...     example="http://remote_site_1/check_mk/",
        ...     )


    Args:
        must_endwith_one: list of str, 1 of which the url must end with
        must_startwith_one: list of str, 1 of which the url must start with

    """

    default_error_messages = {
        "invalid_url": "The URL string {value!r} is not a valid url.",
        "invalid_scheme": "The URL scheme {scheme!r} must be http or https",
        "endswith_error": "The URL {value!r} does not end with {endswith!r}",
        "startwith_error": "The URL {value!r} does not start with {startwith!r}",
    }

    def __init__(
        self,
        required: bool = True,
        description: str = "A URL or part of a URL.",
        must_endwith_one: list[str] | None = None,
        must_startwith_one: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.must_endwith_one = must_endwith_one
        self.must_startwith_one = must_startwith_one

        if self.must_startwith_one:
            validator = validate.URL(
                schemes=set(self.must_startwith_one),
                error=self.error_messages["invalid"],
                require_tld=False,
            )
            self.validators.insert(0, validator)

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.must_endwith_one:
            if not any({value.endswith(postfix) for postfix in self.must_endwith_one}):
                raise self.make_error("endswith_error", value=value, endswith=self.must_endwith_one)

        if self.must_startwith_one:
            if not any({value.startswith(prefix) for prefix in self.must_startwith_one}):
                raise self.make_error(
                    "startwith_error", value=value, startwith=self.must_startwith_one
                )


class Timeout(fields.Float):
    default_error_messages = {
        "too_low": "The timeout {value!r} is less than the minimum {min!r}.",
        "too_high": "The timeout {value!r} is greater than the maximum {max!r} ",
        "negative_value": "The timeout {value!r} is a negative number. ",
    }

    def __init__(
        self,
        required: bool = True,
        minimum: float | None = 0.01,
        maximum: float | None = None,
        description: str = "A timeout value as a decimal number.",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.minimum = minimum
        self.maximum = maximum

    def _validate(self, value: float) -> None:
        super()._validate(value)

        if self.minimum and value < self.minimum:
            raise self.make_error("too_low", value=value, min=self.minimum)

        if self.maximum and value > self.maximum:
            raise self.make_error("too_high", value=value, max=self.maximum)

        if value < 0:
            raise self.make_error("negative_value", value=value)


class UnixPath(fields.String):
    default_error_messages = {
        "should_exist": "The path {path!r} should exist but it doesn't.",
        "should_not_exist": "The path {path!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        required: bool = True,
        description: str = "A unix path",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.presence = presence

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.presence == "should_exist":
            if not path.exists(value):
                raise self.make_error("should_exist", path=value)

        if self.presence == "should_not_exist":
            if path.exists(value):
                raise self.make_error("should_not_exist", path=value)


class NetworkPortNumber(fields.Integer):
    def __init__(self, **kwargs: Any) -> None:
        if "description" not in kwargs:
            kwargs["description"] = "A valid network port number between 1 - 65535."
        super().__init__(
            minimum=1,
            maximum=65535,
            example=6790,
            **kwargs,
        )


class LDAPConnectionID(fields.String):
    default_error_messages = {
        "should_exist": "The LDAP connection {path!r} should exist but it doesn't.",
        "should_not_exist": "The LDAP connection {path!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal["should_exist", "should_not_exist", "ignore"] = "ignore",
        required: bool = True,
        description: str = "An LDAP connection ID string.",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, description=description, **kwargs)
        self.presence = presence

    def _validate(self, value: str) -> None:
        super()._validate(value)

        ldap_connection_ids = [cnx_id for cnx_id, _ in utils.connection_choices()]

        if self.presence == "should_exist":
            if value not in ldap_connection_ids:
                raise self.make_error("should_exist", path=value)

        if self.presence == "should_not_exist":
            if value in ldap_connection_ids:
                raise self.make_error("should_not_exist", path=value)


class AuxTagIDField(fields.String):
    default_error_messages = {
        "should_exist": "The aux_tag {aux_tag_id!r} should exist but it doesn't.",
        "should_not_exist": "The aux_tag {aux_tag_id!r} should not exist but it does.",
        "should_exist_and_should_be_builtin": "The aux_tag {aux_tag_id!r} should be an existing builtin aux tag but it's not.",
        "should_exist_and_should_be_custom": "The aux_tag {aux_tag_id!r} should be an existing custom aux tag but it's not.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist_and_should_be_builtin",
            "should_exist_and_should_be_custom",
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        example: str = "ip-v4",
        description: str = "An auxiliary tag id",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            description=description,
            example=example,
            pattern=r"^[-0-9a-zA-Z_]+\Z",
            **kwargs,
        )
        self.presence = presence

    def _validate(self, value):
        super()._validate(value)
        tag_id = TagID(value)

        if self.presence == "should_exist_and_should_be_builtin":
            if not BuiltinTagConfig().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist_and_should_be_builtin", aux_tag_id=tag_id)

        if self.presence == "should_exist_and_should_be_custom":
            if not load_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist_and_should_be_custom", aux_tag_id=tag_id)

        if self.presence == "should_not_exist":
            if load_all_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_not_exist", aux_tag_id=tag_id)

        if self.presence == "should_exist":
            if not load_all_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist", aux_tag_id=tag_id)


class ContactGroupField(fields.String):
    default_error_messages = {
        "should_exist": "The contact group {contact_group!r} should exist but it doesn't.",
        "should_not_exist": "The contact group {contact_group!r} should not exist but it does.",
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
        super().__init__(
            description="A contact group",
            example="all",
            pattern="^[-a-z0-9A-Z_]*$",
            **kwargs,
        )
        self.presence = presence

    def _validate(self, value: str) -> None:
        super()._validate(value)
        cgs = list(load_contact_group_information())  # list of contact group ids

        if self.presence == "should_exist":
            if value not in cgs:
                raise self.make_error("should_exist", contact_group=value)

        if self.presence == "should_not_exist":
            if value in cgs:
                raise self.make_error("should_not_exist", contact_group=value)


class TimePeriodIDField(fields.String):
    default_error_messages = {
        "should_exist": "The time period {time_period!r} should exist but it doesn't.",
        "should_not_exist": "The time period {time_period!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        description: str = "A time period",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            description=description,
            example="24X7",
            **kwargs,
        )
        self.presence = presence

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.presence == "should_exist":
            if not verify_timeperiod_name_exists(value):
                raise self.make_error("should_exist", time_period=value)

        if self.presence == "should_not_exist":
            if verify_timeperiod_name_exists(value):
                raise self.make_error("should_not_exist", time_period=value)


class SplunkURLField(fields.URL):
    default_error_messages = {
        "invalid_splunk_url": "The url {url!r} must start with https://alert.victorops.com/integrations",
    }

    def __init__(
        self,
        description: str = "A valid splunk webhook URL",
        **kwargs: Any,
    ) -> None:
        self.splunk_url_prefix = "https://alert.victorops.com/integrations"
        super().__init__(
            description=description,
            example=self.splunk_url_prefix + "/example",
            **kwargs,
        )

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if not value.startswith(self.splunk_url_prefix):
            raise self.make_error("invalid_splunk_url", url=value)


class IPField(fields.String):
    default_error_messages = {
        "should_be_ipv4": "The IP address {ip!r} should be ipv4 but it's not.",
        "should_be_ipv6": "The IP address {ip!r} should be ipv6 but it's not.",
        "should_be_ipv4_or_ipv6": "The IP address {ip!r} should be ipv4 or ipv6 but it isn't either.",
    }

    def __init__(
        self,
        ip_type_allowed: Literal["ipv4", "ipv6", "ipv4andipv6"] = "ipv4",
        description: str = "A valid IP address",
        example: str = "127.0.0.1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            description=description,
            example=example,
            **kwargs,
        )
        self.ip_type_allowed = ip_type_allowed
        self.validation_results: list[ValidationError] = []

    def _validate(self, value: str) -> None:
        super()._validate(value)

        if self.ip_type_allowed == "ipv4":
            self._validate_ip4(value)

        if self.ip_type_allowed == "ipv6":
            self._validate_ip6(value)

        for error in self.validation_results:
            raise error

        if self.ip_type_allowed == "ipv4andipv6":
            self._validate_ip4(value)
            self._validate_ip6(value)

            if len(self.validation_results) == 2:
                raise self.make_error("should_be_ipv4_or_ipv6", ip=value)

    def _validate_ip4(self, value: str) -> None:
        try:
            validators.ValidateIPv4()(value)
        except ValidationError:
            self.validation_results.append(self.make_error("should_be_ipv4", ip=value))

    def _validate_ip6(self, value: str) -> None:
        try:
            validators.ValidateIPv6()(value)
        except ValidationError:
            self.validation_results.append(self.make_error("should_be_ipv6", ip=value))


def load_passwords_for_validation():
    return [pw_id for pw_id, _ in PasswordStore()._load_file().items()]


class PasswordStoreIDField(fields.String):
    default_error_messages = {
        "should_exist": "The password store_id {store_id!r} should exist but it doesn't.",
        "should_not_exist": "The password store_id {store_id!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        description: str = "A password store ID",
        example: str = "stored_password_1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            description=description,
            example=example,
            **kwargs,
        )
        self.presence = presence

    def _validate(self, value: str) -> None:
        super()._validate(value)
        pw_ids = load_passwords_for_validation()

        if self.presence == "should_exist":
            if value not in pw_ids:
                raise self.make_error("should_exist", store_id=value)

        if self.presence == "should_not_exist":
            if value in pw_ids:
                raise self.make_error("should_not_exist", store_id=value)


class ServiceLevelField(fields.Integer):
    default_error_messages = {
        "should_exist": "The provided service level {value!r} does not exist. The available service levels are [{choices!r}]",
        "should_not_exist": "The provided service level {value!r} already exists.]",
    }

    def __init__(
        self,
        required: bool = True,
        example: int = 10,
        presence: Literal["should_exist", "should_not_exist"] = "should_exist",
        description: str = "A service level represented as an integer",
        **kwargs: Any,
    ) -> None:
        super().__init__(required=required, example=example, description=description, **kwargs)
        self.presence = presence

    def _validate(self, value):
        super()._validate(value)
        choices = [int_val for int_val, _str_val in active_config.mkeventd_service_levels]

        if self.presence == "should_exist":
            if value not in choices:
                raise self.make_error(
                    "should_exist", value=value, choices=", ".join([str(c) for c in choices])
                )

        if self.presence == "should_not_exist":
            if value in choices:
                raise self.make_error("should_not_exist", value=value)


class TagGroupIDField(fields.String):
    """A field representing the host tag group id"""

    default_error_messages = {
        "should_exist": "The host tag group id {name!r} should exist but it doesn't",
        "should_not_exist": "The host tag group id {name!r} should not exist but it does.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        description: str = "A host tag group id",
        example: str = "piggyback",
        **kwargs: Any,
    ) -> None:
        super().__init__(description=description, example=example, **kwargs)
        self.presence = presence

    def _validate(self, value):
        super()._validate(value)

        if self.presence == "should_exist" and not tag_group_exists(value, builtin_included=True):
            raise self.make_error("should_exist", name=value)

        if self.presence == "should_not_exist" and tag_group_exists(value, builtin_included=True):
            raise self.make_error("should_exist", name=value)
