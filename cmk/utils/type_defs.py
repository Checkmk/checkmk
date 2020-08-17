#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk wide type definitions"""

import abc
import enum
import string
import sys
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Generic,
    List,
    Literal,
    NamedTuple,
    NewType,
    NoReturn,
    Optional,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

HostName = str
HostAddress = str
HostgroupName = str
ServiceName = str
ServicegroupName = str
ContactgroupName = str
TimeperiodName = str
AgentRawData = bytes
RulesetName = str
RuleValue = Any  # TODO: Improve this type
RuleSpec = Dict[str, Any]  # TODO: Improve this type
Ruleset = List[RuleSpec]  # TODO: Improve this type
MetricName = str
CheckPluginNameStr = str
ActiveCheckPluginName = str
Item = Optional[str]
TagValue = str
Labels = Dict[str, str]
LabelSources = Dict[str, str]
TagID = str
TaggroupID = str
Tags = Dict[TagID, TagValue]
TagList = Set[TagValue]
TagGroups = Dict[TagID, TaggroupID]
HostNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                           List[Union[Dict[str, str], str]]]
ServiceNameConditions = Union[None, Dict[str, List[Union[Dict[str, str], str]]],
                              List[Union[Dict[str, str], str]]]
CheckVariables = Dict[str, Any]
Seconds = int
Timestamp = int
TimeRange = Tuple[int, int]

ServiceState = int
HostState = int
ServiceDetails = str
ServiceAdditionalDetails = str
# TODO: Specify this  (see cmk/base/checking.py::_convert_perf_data)
Metric = List
ServiceCheckResult = Tuple[ServiceState, ServiceDetails, List[Metric]]

UserId = NewType("UserId", str)
EventRule = Dict[str, Any]  # TODO Improve this

AgentHash = NewType("AgentHash", str)
AgentConfig = Dict[str, Any]  # TODO Split into more sub configs

# TODO(au): Replace usage with AgentPackagePlatform
# But we need complete typing in cmk.gui.cee.agent_bakery first before we can safely do this.
BakeryOpSys = NewType("BakeryOpSys", str)


class AgentPackagePlatform(enum.Enum):
    LINUX_DEB = "linux_deb"
    LINUX_RPM = "linux_rpm"
    SOLARIS_PKG = "solaris_pkg"
    WINDOWS_MSI = "windows_msi"
    LINUX_TGZ = "linux_tgz"
    SOLARIS_TGZ = "solaris_tgz"
    AIX_TGZ = "aix_tgz"

    def __str__(self) -> str:
        return str(self.value)


class BuiltinBakeryHostName(enum.Enum):
    """ Type for representation of the special agent types
    VANILLA and GENERIC. Yields the same interface as OrdinaryBakeryHostName
    in order to enable a generic handling in one data structure.
    """
    def __init__(self, raw_name: str, name: str) -> None:
        self.raw_name = raw_name
        self._display_name = name

    def __str__(self):
        return self._display_name

    VANILLA = ("_VANILLA", "VANILLA")
    GENERIC = ("_GENERIC", "GENERIC")


class OrdinaryBakeryHostName(str):
    """ Wrapper for normal HostNames, when used as a mapping to an agent,
    that enables a generic handling alongside the special agent types
    VANILLA and GENERIC.
    """
    @property
    def raw_name(self) -> str:
        return self


# Type for entries in data structures that contain both of the above types.
BakeryHostName = Union[Literal[BuiltinBakeryHostName.VANILLA, BuiltinBakeryHostName.GENERIC],
                       OrdinaryBakeryHostName]


class BakerySigningCredentials(TypedDict):
    certificate: str
    private_key: str


# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = Dict[str, Union[str, List[Tuple[str, str]]]]


class ABCName(abc.ABC):
    """Common class for all names.

    A plugin name must be a non-empty string consisting only of letters A-z, digits
    and the underscore.
    """
    VALID_CHARACTERS = string.ascii_letters + '_' + string.digits

    @abc.abstractproperty
    def _legacy_naming_exceptions(self) -> Set[str]:
        """we allow to maintain a list of exceptions"""
        return set()

    def __init__(self, plugin_name: str) -> None:
        self._value = plugin_name
        if plugin_name in self._legacy_naming_exceptions:
            return

        if not isinstance(plugin_name, str):
            raise TypeError("%s must initialized from str" % self.__class__.__name__)
        if not plugin_name:
            raise ValueError("%s initializer must not be empty" % self.__class__.__name__)

        for char in plugin_name:
            if char not in self.VALID_CHARACTERS:
                raise ValueError("invalid character for %s %r: %r" %
                                 (self.__class__.__name__, plugin_name, char))

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %r and %r" % (self, other))
        return self._value == other._value

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError("Can only be compared with %s objects" % self.__class__)
        return self._value < other._value

    def __le__(self, other: Any) -> bool:
        return self < other or self == other

    def __gt__(self, other: Any) -> bool:
        return not self <= other

    def __ge__(self, other: Any) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return hash(type(self).__name__ + self._value)


class ParsedSectionName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


class SectionName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


class RuleSetName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return {
            'drbd.net', 'drbd.disk', 'drbd.stats', 'fileinfo-groups', 'hpux_snmp_cs.cpu',
            'j4p_performance.mem', 'j4p_performance.threads', 'j4p_performance.uptime',
            'j4p_performance.app_state', 'j4p_performance.app_sess', 'j4p_performance.serv_req'
        }


class CheckPluginName(ABCName):
    MANAGEMENT_PREFIX = 'mgmt_'

    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()

    def is_management_name(self) -> bool:
        return self._value.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> 'CheckPluginName':
        if self.is_management_name():
            return self
        return CheckPluginName("%s%s" % (self.MANAGEMENT_PREFIX, self._value))

    def create_host_name(self) -> 'CheckPluginName':
        if self.is_management_name():
            return CheckPluginName(self._value[len(self.MANAGEMENT_PREFIX):])
        return self


class InventoryPluginName(ABCName):
    @property
    def _legacy_naming_exceptions(self) -> Set[str]:
        return set()


class SourceType(enum.Enum):
    """Classification of management sources vs regular hosts"""
    HOST = "HOST"
    MANAGEMENT = "MANAGEMENT"


T_co = TypeVar("T_co", covariant=True)
E_co = TypeVar("E_co", covariant=True)


class Result(Generic[T_co, E_co], abc.ABC):
    """An error container inspired by Rust.

    See Also:
        https://doc.rust-lang.org/std/result/enum.Result.html

    """
    @staticmethod
    def Err(err: E_co):  # type: ignore[misc]
        # mypy complains about the variance of the argument but
        # both static methods only forward it to the respective
        # `__init__()`, which is safe.
        #
        # See Also:
        #   - https://github.com/python/mypy/pull/2888
        #   - https://github.com/python/mypy/issues/7049
        return _Err(err)

    @staticmethod
    def OK(ok: T_co):  # type: ignore[misc]
        # mypy: See comments to Err().
        return _OK(ok)

    @abc.abstractmethod
    def __eq__(self, other: Any) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ok(self) -> Optional[T_co]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def err(self) -> Optional[E_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def is_ok(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def is_err(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def unwrap(self) -> T_co:
        raise NotImplementedError

    @abc.abstractmethod
    def unwrap_err(self) -> E_co:
        raise NotImplementedError

    @abc.abstractmethod
    def unwrap_or(self, default: T_co) -> T_co:  # type: ignore[misc]
        # mypy: See comments to Err().
        raise NotImplementedError

    @abc.abstractmethod
    def unwrap_or_else(self, op: Callable[[E_co], T_co]) -> T_co:
        raise NotImplementedError


class _OK(Result[T_co, E_co]):
    __slots__ = ["_ok"]

    def __init__(self, ok: T_co):
        self._ok: Final[T_co] = ok

    def __repr__(self):
        return "Result.OK(%r)" % self.ok

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if not isinstance(other, _OK):
            return False
        return self.ok == other.ok

    def __hash__(self) -> int:
        return hash(self.ok)

    @property
    def ok(self) -> T_co:
        return self._ok

    @property
    def err(self) -> None:
        return None

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T_co:
        return self.ok

    def unwrap_err(self) -> NoReturn:
        raise ValueError(str(self.ok))

    def unwrap_or(self, default: T_co) -> T_co:  # type: ignore[misc]
        # mypy: See comments to Err().
        return self.ok

    def unwrap_or_else(self, op: Callable[[E_co], T_co]) -> T_co:
        return self.ok


class _Err(Result[T_co, E_co]):
    __slots__ = ["_err"]

    def __init__(self, err: E_co):
        self._err: Final[E_co] = err

    def __repr__(self):
        return "Result.Err(%r)" % self.err

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if not isinstance(other, _Err):
            return False
        return self.err == other.err

    def __hash__(self) -> int:
        return hash(self.err)

    @property
    def ok(self) -> None:
        return None

    @property
    def err(self) -> E_co:
        return self._err

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        raise ValueError(str(self._err))

    def unwrap_err(self) -> E_co:
        return self.err

    def unwrap_or(self, default: T_co) -> T_co:  # type: ignore[misc]
        # mypy: See comments to Err().
        return default

    def unwrap_or_else(self, op: Callable[[E_co], T_co]) -> T_co:
        return op(self.err)


HostKey = NamedTuple("HostKey", [
    ("hostname", HostName),
    ("ipaddress", Optional[HostAddress]),
    ("source_type", SourceType),
])


class OIDSpec:
    """Basic class for OID spec of the form ".1.2.3.4.5" or "2.3"
    """
    VALID_CHARACTERS = '.' + string.digits

    @classmethod
    def validate(cls, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("expected a non-empty string: %r" % (value,))
        if not value:
            raise ValueError("expected a non-empty string: %r" % (value,))

        invalid = ''.join(c for c in value if c not in cls.VALID_CHARACTERS)
        if invalid:
            raise ValueError("invalid characters in OID descriptor: %r" % invalid)

        if value.endswith('.'):
            raise ValueError("%r should not end with '.'" % (value,))

    def __init__(self, value: str) -> None:
        self.validate(value)
        self._value = value


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = u"") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception("invalid timeperiod alias %r" % (alias,))


class EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __str__(self):
        return super().__repr__()

    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return '1e%d' % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return '-1e%d' % (sys.float_info.max_10_exp + 1)
        return super().__repr__()
