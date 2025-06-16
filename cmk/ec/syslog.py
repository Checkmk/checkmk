#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

import socket
from codecs import BOM_UTF8
from collections.abc import Iterable, Mapping
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal

import cmk.utils.paths

from .settings import create_paths


class SyslogPriority:
    NAMES: Mapping[int, str] = {
        0: "emerg",
        1: "alert",
        2: "crit",
        3: "err",
        4: "warning",
        5: "notice",
        6: "info",
        7: "debug",
    }

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"SyslogPriority({self.value})"

    def __str__(self) -> str:
        try:
            return self.NAMES[self.value]
        except KeyError:
            return f"(unknown priority {self.value})"


class SyslogFacility:
    NAMES: Mapping[int, str] = {
        0: "kern",
        1: "user",
        2: "mail",
        3: "daemon",
        4: "auth",
        5: "syslog",
        6: "lpr",
        7: "news",
        8: "uucp",
        9: "cron",
        10: "authpriv",
        11: "ftp",
        12: "ntp",
        13: "logaudit",
        14: "logalert",
        15: "clock",
        16: "local0",
        17: "local1",
        18: "local2",
        19: "local3",
        20: "local4",
        21: "local5",
        22: "local6",
        23: "local7",
        30: "logfile",  # HACK because the RFC says that facilities MUST be in the range 0-23
        31: "snmptrap",  # everything above that is for internal use. see: https://datatracker.ietf.org/doc/html/rfc5424#section-6.2.1
    }

    def __init__(self, value: int) -> None:
        if value not in self.NAMES:
            raise ValueError(
                f"Value must be one of the following {', '.join(str(key) for key in self.NAMES)}"
            )
        self.value = int(value)

    def __repr__(self) -> str:
        return f"SyslogFacility({self.value})"

    def __str__(self) -> str:
        try:
            return self.NAMES[self.value]
        except KeyError:
            return f"(unknown facility {self.value})"


_NILVALUE: Literal["-"] = "-"  # NILVALUE from RFC 5424
_PRINTUSASCII = set(map(chr, range(33, 127)))  # PRINTUSASCII from RFC 5424


def _1_n_printusascii_conform(
    n: int,
    to_check: str,
) -> bool:
    """
    Checks if a string contains is conform with 1*<n>PRINTUSASCII
    (https://tools.ietf.org/html/rfc5424)
    >>> _1_n_printusascii_conform(20, 'abc123')
    True
    >>> _1_n_printusascii_conform(1, 'abc123')
    False
    >>> _1_n_printusascii_conform(1, '')
    False
    >>> _1_n_printusascii_conform(20, 'ÄÜÖ $#')
    False
    """
    return (0 < len(to_check) <= n) and set(to_check.lower()).issubset(_PRINTUSASCII)


def _validate_sd_name(name: str) -> bool:
    """
    Checks if input is a valid SD-NAME from https://tools.ietf.org/html/rfc5424
    >>> _validate_sd_name('abc123')
    True
    >>> _validate_sd_name('abc123' * 10)
    False
    >>> _validate_sd_name('abc=12]3')
    False
    """
    return _1_n_printusascii_conform(32, name) and not any(
        forbidden_char in name for forbidden_char in ("=", " ", "]", '"')
    )


class StructuredDataName:
    """Represents SD-NAME from https://tools.ietf.org/html/rfc5424"""

    def __init__(self, name: str) -> None:
        if not _validate_sd_name(name):
            raise ValueError(f"{name} is not an RFC 5425-conform SD-NAME.")
        self.__name = name

    @property
    def name(self) -> str:
        return self.__name

    def __repr__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, StructuredDataName):
            return self.name == o.name
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


class StructuredDataID:
    """Represents SD-ID from https://tools.ietf.org/html/rfc5424"""

    def __init__(self, id_: str) -> None:
        if not self._validate(id_):
            raise ValueError(f"{id_} is not an RFC 5425-conform SD-ID.")
        self.__id = id_

    @property
    def id(self) -> str:
        return self.__id

    def __repr__(self) -> str:
        return self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, StructuredDataID):
            return NotImplemented
        return self.id == o.id

    @staticmethod
    def _validate(id_: str) -> bool:
        is_valid = _validate_sd_name(id_)
        if "@" not in id_:
            return is_valid

        try:
            _id_name, enterprise_num = id_.split("@")
            try:
                int(enterprise_num)
            except ValueError:
                return False
        except ValueError:
            return False

        return is_valid


class StructuredDataValue:
    """Represents SD-VALUE from https://tools.ietf.org/html/rfc5424"""

    def __init__(self, value: str) -> None:
        if "\n" in value:
            raise ValueError("Structured data values must not contain linebreaks.")
        self.__value = value

    def __repr__(self) -> str:
        value_escaped = self.__value
        for char_to_escape in (
            "\\",
            '"',
            "]",
        ):
            value_escaped = value_escaped.replace(char_to_escape, rf"\{char_to_escape}")
        return value_escaped


class StructuredDataParameters(dict[StructuredDataName, StructuredDataValue]):
    """Represents SD-PARAMs of one SD-ELEMENT from https://tools.ietf.org/html/rfc5424"""

    def __repr__(self) -> str:
        return " ".join(f'{repr(name)}="{repr(value)}"' for name, value in self.items())


class StructuredData(dict[StructuredDataID, StructuredDataParameters]):
    """Represents STRUCTURED-DATA from https://tools.ietf.org/html/rfc5424"""

    def __repr__(self) -> str:
        if not self:
            return _NILVALUE
        return "".join(
            f"[{repr(sd_id)}{' ' if sd_params else ''}{repr(sd_params)}]"
            for sd_id, sd_params in self.items()
        )


class SyslogMessage:
    """Represents a syslog message which can be sent to the EC. Sticks to the Syslog Message Format,
    see https://tools.ietf.org/html/rfc5424.
    """

    _CHECKMK_SD_ID = StructuredDataID("Checkmk@18662")
    _ENCODING = "utf-8"

    def __init__(
        self,
        *,
        facility: int,
        severity: int,
        timestamp: float | Literal["-"] = _NILVALUE,
        host_name: str = _NILVALUE,
        application: str = _NILVALUE,
        proc_id: str = _NILVALUE,
        msg_id: str = _NILVALUE,
        structured_data: StructuredData | None = None,
        text: str | None = None,
        ip_address: str | None = None,
        service_level: int | None = None,
    ) -> None:
        structured_data = structured_data or StructuredData({})

        syslog_facility = SyslogFacility(facility)

        if not 0 <= severity <= 7:
            raise ValueError("Severity must be in the range 0..7 (inclusive).")

        if self._CHECKMK_SD_ID in structured_data:
            raise ValueError("Structured data must not contain element with Checkmk SD-ID")

        self._priority = (syslog_facility.value << 3) + severity
        self._timestamp = (
            _NILVALUE if isinstance(timestamp, str) else self._unix_timestamp_to_rfc_5424(timestamp)
        )

        self._sd = self._add_ip_and_sl_to_structured_data(
            structured_data,
            ip_address,
            service_level,
        )

        if _1_n_printusascii_conform(255, host_name):
            self._host_name = host_name
        else:
            self._host_name = _NILVALUE
            self._sd[self._CHECKMK_SD_ID][StructuredDataName("host")] = StructuredDataValue(
                host_name
            )

        if _1_n_printusascii_conform(48, application):
            self._application = application
        else:
            self._application = _NILVALUE
            self._sd[self._CHECKMK_SD_ID][StructuredDataName("application")] = StructuredDataValue(
                application
            )

        if _1_n_printusascii_conform(128, proc_id):
            self._proc_id = proc_id
        else:
            self._proc_id = _NILVALUE
            self._sd[self._CHECKMK_SD_ID][StructuredDataName("pid")] = StructuredDataValue(proc_id)

        if _1_n_printusascii_conform(32, msg_id):
            self._msg_id = msg_id
        else:
            self._msg_id = _NILVALUE
            self._sd[self._CHECKMK_SD_ID][StructuredDataName("msg_id")] = StructuredDataValue(
                msg_id
            )

        self._text = text

    @staticmethod
    def _unix_timestamp_to_rfc_5424(unix_timestamp: float) -> str:
        """
        >>> SyslogMessage._unix_timestamp_to_rfc_5424(1618243591)
        '2021-04-12T16:06:31+00:00'
        >>> SyslogMessage._unix_timestamp_to_rfc_5424(1618243591.1234)
        '2021-04-12T16:06:31.123400+00:00'
        """
        return datetime.fromtimestamp(unix_timestamp, tz=UTC).isoformat()

    @classmethod
    def _add_ip_and_sl_to_structured_data(
        cls,
        structured_data: StructuredData,
        ip_address: str | None,
        service_level: int | None,
    ) -> StructuredData:
        checkmk_sd_params = {}
        if ip_address:
            checkmk_sd_params[StructuredDataName("ipaddress")] = StructuredDataValue(ip_address)
        if service_level:
            checkmk_sd_params[StructuredDataName("sl")] = StructuredDataValue(str(service_level))
        return StructuredData(
            {
                **structured_data,
                cls._CHECKMK_SD_ID: StructuredDataParameters(checkmk_sd_params),
            }
        )

    def __repr__(self) -> str:
        return (
            f"<{self._priority}>1 "
            f"{self._timestamp} "
            f"{self._host_name} "
            f"{self._application} "
            f"{self._proc_id} "
            f"{self._msg_id} "
            f"{repr(self._sd)}"
            f"{(' ' + self._bom(self._text) + self._text) if self._text else ''}"
        )

    def __bytes__(self) -> bytes:
        return repr(self).encode(self._ENCODING)

    @classmethod
    def _bom(
        cls,
        txt: str,
    ) -> str:
        return "" if txt.isascii() else BOM_UTF8.decode(cls._ENCODING)


def forward_to_unix_socket(
    syslog_messages: Iterable[SyslogMessage],
    path: Path | None = None,
    conn_timeout: float | None = None,
) -> None:
    payload = b"".join(bytes(msg) + b"\n" for msg in syslog_messages)
    if not payload:
        return  # optimization: no need for any I/O
    if path is None:
        path = create_paths(cmk.utils.paths.omd_root).event_socket.value
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(conn_timeout)
        sock.connect(str(path))
        sock.sendall(payload)
