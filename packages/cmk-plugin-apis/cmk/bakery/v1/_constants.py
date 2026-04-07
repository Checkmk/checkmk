#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from enum import auto, Enum, StrEnum, unique


@unique
class OS(Enum):
    """Describes an operating system in the context of the Bakery API."""

    LINUX = "linux"
    SOLARIS = "solaris"
    AIX = "aix"
    WINDOWS = "windows"

    def __str__(self) -> str:
        return str(self.value)


@unique
class DebStep(StrEnum):
    """Describes a step in the processing of a DEB package.

    For details refer to `Maintainer Scripts
    <https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html>`_.
    """

    PREINST = auto()
    POSTINST = auto()
    PRERM = auto()
    POSTRM = auto()


@unique
class RpmStep(StrEnum):
    """Describes a step in the processing of a RPM package.

    For details refer to `Scriptlets
    <https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/>`_.
    """

    PRE = auto()
    POST = auto()
    PREUN = "preun"
    POSTUN = auto()
    PRETRANS = auto()
    POSTTRANS = auto()


class SolStep(StrEnum):
    """Describes a step in the processing of a Solaris PKG package.

    For details refer to `Writing Procedure Scripts
    <https://docs.oracle.com/cd/E26505_01/html/E28550/ch3enhancepkg-10289.html#ch3enhancepkg-14637>`_.
    """

    PREINSTALL = auto()
    POSTINSTALL = auto()
    PREREMOVE = auto()
    POSTREMOVE = auto()


PkgStep = DebStep | RpmStep | SolStep

WindowsConfigContent = int | str | bool | dict | list
"""Allowed types for the 'content' argument of windows config artifacts
To be used for type annotations"""
