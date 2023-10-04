#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import auto, Enum, StrEnum, unique


@unique
class OS(Enum):
    """Describes an operating system in the context of the Bakery API."""

    LINUX = "linux"
    """Describes a Linux target system"""
    SOLARIS = "solaris"
    """Describes a Solaris target system"""
    AIX = "aix"
    """Describes an AIX target system"""
    WINDOWS = "windows"
    """Describes a Windows target system"""

    def __str__(self) -> str:
        return str(self.value)


@unique
class DebStep(StrEnum):
    """Describes a step in the processing of a DEB package."""

    PREINST = auto()
    "Describes a maintainer script, that will be executed before package installation"
    POSTINST = auto()
    "Describes a maintainer script, that will be executed right after package installation"
    PRERM = auto()
    "Describes a maintainer script, that will be executed right before package uninstallation"
    POSTRM = auto()
    "Describes a maintainer script, that will be executed after package uninstallation"


@unique
class RpmStep(StrEnum):
    """Describes a step in the processing of a RPM package."""

    PRE = auto()
    "Describes a scriptlet, that will be executed before package installation"
    POST = auto()
    "Describes a scriptlet, that will be executed right after package installation"
    PREUN = "preun"
    "Describes a scriptlet, that will be executed right before package uninstallation"
    POSTUN = auto()
    "Describes a scriptlet, that will be executed right after package uninstallation"
    PRETRANS = auto()
    "Describes a scriptlet, that will be executed before a complete package transaction"
    POSTTRANS = auto()
    "Describes a scriptlet, that will be executed after a complete package transaction"


class SolStep(StrEnum):
    """Describes a step in the processing of a Solaris PKG package."""

    PREINSTALL = auto()
    "Describes an installation script, that will be executed before package installation"
    POSTINSTALL = auto()
    "Describes an installation script, that will be executed right after package installation"
    PREREMOVE = auto()
    "Describes an installation script, that will be executed right before package uninstallation"
    POSTREMOVE = auto()
    "Describes an installation script, that will be executed after package uninstallation"


PkgStep = DebStep | RpmStep | SolStep

WindowsConfigContent = int | str | bool | dict | list
"""Allowed types for the 'content' argument of windows config artifacts
To be used for type annotations"""
