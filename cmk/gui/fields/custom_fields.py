#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from os import path
from typing import Any, Literal

from marshmallow import validate

from cmk.gui.plugins.userdb import utils

from cmk import fields


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
