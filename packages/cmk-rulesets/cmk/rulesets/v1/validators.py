#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.
import enum
import re
from collections.abc import Sequence
from typing import Final, Sized
from urllib.parse import urlparse

from cmk.rulesets.v1._localize import Localizable


class ValidationError(ValueError):
    """Raise when custom validation found invalid values

    Args:
        message: Description of why the value is invalid
    """

    def __init__(self, message: Localizable) -> None:
        super().__init__(message)
        self._message = message

    @property
    def message(self) -> Localizable:
        return self._message


class DisallowEmpty:  # pylint: disable=too-few-public-methods
    """Custom validator that makes sure the validated value is not empty."""

    def __init__(self, error_msg: Localizable | None = None) -> None:
        self.error_msg: Final = error_msg or Localizable("An empty value is not allowed here.")

    def __call__(self, value: Sequence[object]) -> None:
        if value is None or (isinstance(value, Sized) and len(value) == 0):
            raise ValidationError(self.error_msg)


class InRange:  # pylint: disable=too-few-public-methods
    """Custom validator that ensures the validated value is in a given interval."""

    def __init__(
        self,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        error_msg: Localizable | None = None,
    ) -> None:
        self.range: Final = (min_value, max_value)
        self.error_msg: Final = (
            self._get_default_errmsg(min_value, max_value) if error_msg is None else error_msg
        )

    @staticmethod
    def _get_default_errmsg(min_: float | None, max_: float | None) -> Localizable:
        if min_ is None:
            if max_ is None:
                return Localizable("This message is not supposed to be used. Ever.")
            return Localizable("The maximum allowed value is %s.") % str(max_)

        if max_ is None:
            return Localizable("The minimum allowed value is %s.") % str(min_)
        return Localizable("Allowed values range from %s to %s.") % (str(min_), str(max_))

    def __call__(self, value: int | float) -> None:
        if self.range[0] is not None and value < self.range[0]:
            raise ValidationError(self.error_msg)
        if self.range[1] is not None and self.range[1] < value:
            raise ValidationError(self.error_msg)


class MatchRegex:  # pylint: disable=too-few-public-methods
    """Custom validator that ensures the validated value matches the given regular expression."""

    def __init__(self, regex: re.Pattern[str] | str, error_msg: Localizable | None = None) -> None:
        self.regex: Final = re.compile(regex) if isinstance(regex, str) else regex
        self.error_msg: Final = error_msg or (
            Localizable("Your input does not match the required format '%s'.") % self.regex.pattern
        )

    def __call__(self, value: str) -> None:
        if not self.regex.match(value):
            raise ValidationError(self.error_msg)


class NetworkPort:  # pylint: disable=too-few-public-methods
    """Validator that ensures that an integer is in the network port range"""

    def __init__(self, error_msg: Localizable | None = None) -> None:
        self.error_msg: Final = error_msg or (
            Localizable("Your input does not match the required port range 0-65535.")
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


class Url:  # pylint: disable=too-few-public-methods
    """Custom validator that ensures the validated value is a URL with the specified scheme."""

    def __init__(
        self, protocols: Sequence[UrlProtocol], error_msg: Localizable | None = None
    ) -> None:
        self.protocols: Final = protocols
        self.error_msg: Final = error_msg or (
            Localizable("Your input is not a valid URL conforming to any allowed protocols ('%s').")
            % str(", ".join(self.protocols))
        )

    def __call__(self, value: str) -> None:
        parts = urlparse(value)
        if not parts.scheme or not parts.netloc or parts.scheme not in self.protocols:
            raise ValidationError(self.error_msg)
