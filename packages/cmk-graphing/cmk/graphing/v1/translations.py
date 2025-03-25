#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "PassiveCheck",
    "ActiveCheck",
    "HostCheckCommand",
    "NagiosPlugin",
    "RenameTo",
    "ScaleBy",
    "RenameToAndScaleBy",
]


@dataclass(frozen=True)
class PassiveCheck:
    """
    A passive check has the prefix ``check_mk-``.

    Args:
        name: The name of the passive check.

    Example:

        >>> PassiveCheck("check_plugin")
        PassiveCheck(name='check_plugin')
    """

    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class ActiveCheck:
    """
    An active check has the prefix ``check_mk_active-``.

    Args:
        name: The name of the active check

    Example:

        >>> ActiveCheck("http")
        ActiveCheck(name='http')
    """

    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class HostCheckCommand:
    """
    A host check command has the prefix ``check-mk-``.

    Args:
        name: The name of the host check command

    Example:

        >>> HostCheckCommand("host-ping")
        HostCheckCommand(name='host-ping')
    """

    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class NagiosPlugin:
    """
    A classical Nagios plug-in has the prefix ``check_``.

    Args:
        name: The name of the Nagios plug-in

    Example:

        >>> NagiosPlugin("check_plugin")
        NagiosPlugin(name='check_plugin')
    """

    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class RenameTo:
    """
    Args:
        metric_name: A new metric name

    Example:

        >>> RenameTo("new-metric-name")
        RenameTo(metric_name='new-metric-name')
    """

    metric_name: str

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)


@dataclass(frozen=True)
class ScaleBy:
    """
    Args:
        factor: A number with which the old metric is scaled

    Example:

        >>> ScaleBy(1.5)
        ScaleBy(factor=1.5)
    """

    factor: int | float

    def __post_init__(self) -> None:
        assert self.factor


@dataclass(frozen=True)
class RenameToAndScaleBy:
    """
    Args:
        metric_name: A new metric name
        factor: A number with which the old metric is scaled

    Example:

        >>> RenameToAndScaleBy("new-metric-name", 1.5)
        RenameToAndScaleBy(metric_name='new-metric-name', factor=1.5)
    """

    metric_name: str
    factor: int | float

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)
        assert self.factor


@dataclass(frozen=True, kw_only=True)
class Translation:
    """
    A translation applies to the given check commands and renames or scales given old metrics to new
    ones.

    Instances of this class will only be picked up by Checkmk if their names start with
    ``translation_``.

    Args:
        name: An unique name
        check_commands: A list of check commands to which the translations apply
        translations: A map which defines how old metrics are renamed or scaled

    Example:

        >>> translation_name = Translation(
        ...     name="name",
        ...     check_commands=[PassiveCheck("check_plugin_name")],
        ...     translations={
        ...         "old-metric-name-1": RenameTo("new-metric-name-1"),
        ...         "old-metric-name-2": ScaleBy(1.5),
        ...         "old-metric-name-3": RenameToAndScaleBy("new-metric-name-3", 1.5),
        ...     },
        ... )
    """

    name: str
    check_commands: Sequence[PassiveCheck | ActiveCheck | HostCheckCommand | NagiosPlugin]
    translations: Mapping[str, RenameTo | ScaleBy | RenameToAndScaleBy]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.check_commands and self.translations
        for name in self.translations:
            if isinstance(name, str) and not name:
                raise ValueError(self.name)
