#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deprecation Warnings

This module defines a set of deprecation warning classes for Checkmk. These warnings are used to
inform developers about features that are deprecated and will be removed in future releases of
Checkmk.

Marking the code like this allows us to keep track of deprecation and not miss any scheduled
removal, due to being reminded by the warnings.

Example usage:
    warnings.warn("Don't use foo anymore. Use baz instead.", DeprecatedSince22Warning)

When used like this, the warning will show up in each pytest run when the relevant section of code
is triggered. It won't show up in user's log files.

Note:
    The policy for removal is typically two releases after the feature's initial deprecation,
    although internal changes can sometimes allow for earlier removal.

"""


class CMKDeprecationWarning(DeprecationWarning):
    """A deprecation warning.

    Attributes:
        message: Description of the warning.
        since: Checkmk version in what the deprecation was introduced.
        expected_removal: Checkmk version in what the corresponding functionality expected to be removed.
    """

    message: str
    since: tuple[int, int]
    expected_removal: tuple[int, int] | None

    def __init__(
        self,
        message: str,
        *args: object,
        since: tuple[int, int],
        expected_removal: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(message, *args)
        self.message = message.rstrip(".")
        self.since = since
        self.expected_removal = expected_removal

    def __str__(self) -> str:
        msg = [f"{self.message}. Deprecated since Checkmk {self.since[0]}.{self.since[1]}"]
        if self.expected_removal is not None:
            msg.append(
                f" to be removed in Checkmk {self.expected_removal[0]}.{self.expected_removal[1]}."
            )
        else:
            msg.append(".")
        return "".join(msg)


class DeprecatedSince16Warning(CMKDeprecationWarning):
    """This feature is deprecated since Checkmk 1.6"""

    def __init__(self, message: str):
        super().__init__(message, since=(1, 6), expected_removal=(2, 1))


class DeprecatedSince20Warning(CMKDeprecationWarning):
    """This feature is deprecated since Checkmk 2.0"""

    def __init__(self, message: str):
        super().__init__(message, since=(2, 0), expected_removal=(2, 2))


class DeprecatedSince21Warning(CMKDeprecationWarning):
    """This feature is deprecated since Checkmk 2.1"""

    def __init__(self, message: str):
        super().__init__(message, since=(2, 1), expected_removal=(2, 3))


class DeprecatedSince22Warning(CMKDeprecationWarning):
    """This feature is deprecated since Checkmk 2.2"""

    def __init__(self, message: str):
        super().__init__(message, since=(2, 2), expected_removal=(2, 4))


class DeprecatedSince23Warning(CMKDeprecationWarning):
    """This feature is deprecated since Checkmk 2.3"""

    def __init__(self, message: str):
        super().__init__(message, since=(2, 3), expected_removal=(2, 5))
