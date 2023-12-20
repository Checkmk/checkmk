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
    Defines a passive check

    A passive check has the prefix 'check_mk-'.

    Args:
        name:   The name of the passive check

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
    Defines an active check

    An active check has the prefix 'check_mk_active-'.

    Args:
        name:   The name of the active check

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
    Defines a host check command

    A host check command has the prefix 'check-mk-'.

    Args:
        name:   The name of the host check command

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
    Defines a classical Nagios plugin

    A classical Nagios plugin has the prefix 'check_'.

    Args:
        name:   The name of the Nagios plugin

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
    Defines a 'rename to'

    Args:
        rename_to:
                A new metric name

    Example:

        >>> RenameTo("new-metric-name")
        RenameTo(rename_to='new-metric-name')

    """

    rename_to: str

    def __post_init__(self) -> None:
        if not self.rename_to:
            raise ValueError(self.rename_to)


@dataclass(frozen=True)
class ScaleBy:
    """
    Defines a 'scale by'

    Args:
        scale_by:
                A number with which the old metric is scaled

    Example:

        >>> ScaleBy(1.5)
        ScaleBy(scale_by=1.5)

    """

    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.scale_by


@dataclass(frozen=True)
class RenameToAndScaleBy:
    """
    Defines a 'rename to' and 'scale by'

    Args:
        rename_to:
                A new metric name
        scale_by:
                A number with which the old metric is scaled

    Example:

        >>> RenameToAndScaleBy("new-metric-name", 1.5)
        RenameToAndScaleBy(rename_to='new-metric-name', scale_by=1.5)

    """

    rename_to: str
    scale_by: int | float

    def __post_init__(self) -> None:
        if not self.rename_to:
            raise ValueError(self.rename_to)
        assert self.scale_by


@dataclass(frozen=True, kw_only=True)
class Translation:
    """
    Defines a translation

    A translation applies to the given check commands and renames or scales given old metrics to new
    ones.

    Args:
        name:   An unique name
        check_commands:
                A list of check commands to which the translations apply
        translations:
                A map which defines how old metrics are renamed or scaled

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
