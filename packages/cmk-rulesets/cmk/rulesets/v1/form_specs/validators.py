#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import ipaddress
import re
from collections.abc import Sequence, Sized
from typing import Final
from urllib.parse import urlparse

from .._localize import Message


class ValidationError(ValueError):
    """Raise when custom validation found invalid values

    Args:
        message: Description of why the value is invalid
    """

    def __init__(self, message: Message) -> None:
        super().__init__(message)
        self._message = message

    @property
    def message(self) -> Message:
        return self._message


class LengthInRange:
    """Custom validator that ensures the validated size is in a given interval."""

    def __init__(
        self,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        error_msg: Message | None = None,
    ) -> None:
        self.range: Final = (min_value, max_value)
        self.error_msg: Final = (
            self._get_default_errmsg(min_value, max_value) if error_msg is None else error_msg
        )

    @staticmethod
    def _get_default_errmsg(min_: float | None, max_: float | None) -> Message:
        if min_ is None:
            if max_ is None:
                raise ValidationError(
                    Message(
                        "Either the minimum or maximum allowed value must be "
                        "configured, otherwise this validator is meaningless."
                    )
                )
            return Message("The maximum allowed length is %s.") % str(max_)

        if max_ is None:
            return Message("The minimum allowed length is %s.") % str(min_)
        return Message("Allowed lengths range from %s to %s.") % (str(min_), str(max_))

    def __call__(self, value: Sized) -> None:
        if self.range[0] is not None and len(value) < self.range[0]:
            raise ValidationError(self.error_msg)
        if self.range[1] is not None and self.range[1] < len(value):
            raise ValidationError(self.error_msg)


class NumberInRange:
    """Custom validator that ensures the validated number is in a given interval."""

    def __init__(
        self,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        error_msg: Message | None = None,
    ) -> None:
        self.range: Final = (min_value, max_value)
        self.error_msg: Final = (
            self._get_default_errmsg(min_value, max_value) if error_msg is None else error_msg
        )

    @staticmethod
    def _get_default_errmsg(min_: float | None, max_: float | None) -> Message:
        if min_ is None:
            if max_ is None:
                raise ValidationError(
                    Message(
                        "Either the minimum or maximum allowed value must be "
                        "configured, otherwise this validator is meaningless."
                    )
                )
            return Message("The maximum allowed value is %s.") % str(max_)

        if max_ is None:
            return Message("The minimum allowed value is %s.") % str(min_)
        return Message("Allowed values range from %s to %s.") % (str(min_), str(max_))

    def __call__(self, value: int | float) -> None:
        if self.range[0] is not None and value < self.range[0]:
            raise ValidationError(self.error_msg)
        if self.range[1] is not None and self.range[1] < value:
            raise ValidationError(self.error_msg)


class RegexGroupsInRange:
    """Custom validator that ensures the validated value is in a given interval."""

    def __init__(
        self,
        min_groups: int | None = None,
        max_groups: int | None = None,
        error_msg: Message | None = None,
    ) -> None:
        self.range: Final = (min_groups, max_groups)
        self.error_msg: Final = (
            self._get_default_errmsg(min_groups, max_groups) if error_msg is None else error_msg
        )

    @staticmethod
    def _get_default_errmsg(min_: float | None, max_: float | None) -> Message:
        if min_ is None:
            if max_ is None:
                raise ValidationError(
                    Message(
                        "Either the minimum or maximum number of allowed groups must be configured,"
                        " otherwise this validator is meaningless."
                    )
                )
            return Message("The maximum allowed number of regex groups is %s.") % str(max_)

        if max_ is None:
            return Message("The minimum allowed number of regex groups is %s.") % str(min_)
        return Message("Allowed number of regex groups ranges from %s to %s.") % (
            str(min_),
            str(max_),
        )

    def __call__(self, pattern: str) -> None:
        compiled = re.compile(pattern)
        if self.range[0] is not None and compiled.groups < self.range[0]:
            raise ValidationError(self.error_msg)
        if self.range[1] is not None and self.range[1] < compiled.groups:
            raise ValidationError(self.error_msg)


class MatchRegex:
    """Custom validator that ensures the validated value matches the given regular expression."""

    def __init__(self, regex: re.Pattern[str] | str, error_msg: Message | None = None) -> None:
        self.regex: Final = re.compile(regex) if isinstance(regex, str) else regex
        self.error_msg: Final = error_msg or (
            Message("Your input does not match the required format '%s'.") % self.regex.pattern
        )

    def __call__(self, value: str) -> None:
        if not self.regex.match(value):
            raise ValidationError(self.error_msg)


class NetworkPort:
    """Validator that ensures that an integer is in the network port range"""

    def __init__(self, error_msg: Message | None = None) -> None:
        self.error_msg: Final = error_msg or (
            Message("Your input does not match the required port range 0-65535.")
        )

    def __call__(self, value: int) -> None:
        if value < 0 or value > 65535:
            raise ValidationError(self.error_msg)


class UrlProtocol(enum.StrEnum):
    FILE = "file"
    FTP = "ftp"
    GOPHER = "gopher"
    HDL = "hdl"
    HTTP = "http"
    HTTPS = "https"
    IMAP = "imap"
    MAILTO = "mailto"
    MMS = "mms"
    NEWS = "news"
    NNTP = "nntp"
    PROSPERO = "prospero"
    RSYNC = "rsync"
    RTSP = "rtsp"
    RTSPS = "rtsps"
    RTSPU = "rtspu"
    SFTP = "sftp"
    SHTTP = "shttp"
    SIP = "sip"
    SIPS = "sips"
    SNEWS = "snews"
    SNV = "svn"
    SVNSSH = "svn+ssh"
    TELNET = "telnet"
    WAIS = "wais"
    WS = "ws"
    WSS = "wss"


class Url:
    """Custom validator that ensures the validated value is a URL with the specified scheme."""

    def __init__(self, protocols: Sequence[UrlProtocol], error_msg: Message | None = None) -> None:
        self.protocols: Final = protocols
        self.error_msg: Final = error_msg or (
            Message("Your input is not a valid URL conforming to any allowed protocols ('%s').")
            % str(", ".join(self.protocols))
        )

    def __call__(self, value: str) -> None:
        try:
            parts = urlparse(value)
        except ValueError as exc:
            raise ValidationError(Message("%s") % str(exc))

        if not parts.scheme or not parts.netloc or parts.scheme not in self.protocols:
            raise ValidationError(self.error_msg)


class EmailAddress:
    """Validator that ensures the validated value is an email address"""

    def __init__(self, error_msg: Message | None = None) -> None:
        self.error_msg: Final = error_msg or (Message("Your input is not a valid email address."))

    def __call__(self, value: str) -> None:
        # According to RFC5322 an email address is defined as:
        #     address = name-addr / addr-spec / group
        # We only allow the dot-atom of addr-spec here:
        #     addr-spec = (dot-atom / quoted-string / obs-local-part) "@" domain
        #     dot-atom = [CFWS] 1*atext *("." 1*atext) [CFWS]
        #     atext = ALPHA / DIGIT / "!" / "#" /  ; Printable US-ASCII
        #             "$" / "%" / "&" / "'"        ;  characters not including
        #             "&" / "'" / "*" / "+"        ;  specials. Used for atoms.
        #             "-" / "/" / "=" / "?"
        #             "^" / "_" / "`" / "{"
        #             "|" / "}" / "~"
        # with the additional extension of atext to the addr-spec as specified
        # by RFC6531:
        #     atext   =/  UTF8-non-ascii
        # Furthermore we do not allow comments inside CFWS and any leading or
        # trailing whitespace in the address is removed.
        #
        # The domain part of addr-spec is defined as:
        #     domain = dot-atom / domain-literal / obs-domain
        # We only allow dot-atom with a restricted character of [A-Z0-9.-] and a
        # length of 2-24 for the top level domain here. Although top level domains
        # may be longer the longest top level domain currently in use is 24
        # characters wide. Check this out with:
        #     wget -qO - http://data.iana.org/TLD/tlds-alpha-by-domain.txt | tail -n+2 | wc -L
        #
        # Note that the current regex allows multiple subsequent "." which are
        # not allowed by RFC5322.

        email_regex = re.compile(
            r"^[\w.!#$%&'*+-=?^`{|}~]+@(localhost|[\w.-]+\.[\w]{2,24})$", re.I | re.UNICODE
        )
        if not email_regex.match(value):
            raise ValidationError(self.error_msg)


class HostAddress:
    """Validator that ensures the validated value is a hostname or IP address.

    It does not resolve the hostname or check if the IP address is reachable.
    """

    def __init__(self, error_msg: Message | None = None) -> None:
        self.error_msg: Final = error_msg or (
            Message("Your input is not a valid hostname or IP address.")
        )

    def _validate_ipaddress(self, value: str) -> None:
        ipaddress.ip_address(value)

    def _validate_hostname(self, value: str) -> None:
        total_length = len(value)
        if value.endswith("."):
            value = value[:-1]
            total_length -= 1

        if total_length > 253:
            raise ValidationError(self.error_msg)

        labels = value.split(".")

        if any(len(label) > 63 for label in labels):
            raise ValidationError(self.error_msg)

        pattern = r"(?!-)[a-z0-9-]{1,63}(?<!-)$"
        allowed = re.compile(pattern, re.IGNORECASE)

        # TLD must not be all numeric
        if re.match(r"[0-9]+$", labels[-1]):
            raise ValidationError(self.error_msg)

        # Check each label
        for label in labels:
            if (not label) or (not allowed.match(label)):
                raise ValidationError(self.error_msg)

    def __call__(self, value: str) -> None:
        if not value:
            raise ValidationError(self.error_msg)

        try:
            self._validate_ipaddress(value)
            return
        except ValueError:
            pass

        self._validate_hostname(value)
