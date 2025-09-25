#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
from typing import NamedTuple


class Secret(NamedTuple):
    # it seems that NamedTuple is the most reasonable way to create a pydantic compatible class
    # without adding a dependency on pydantic
    """Represents a configured secret to the bakery plugin

    This class aims to reduce the chances of accidentally exposing the secret in crash reports and log messages.
    However, a bakery plug-in produces configuration files that are deployed to the target system.
    Therefor the plugin needs access to the actual secret.
    As a result, we cannot guarantee that bakery plugins will not expose the secret in any way:

    Example:

        # This is passed by the backend to the bakery plugin
        >>> s = Secret("s3cr3t", "", "")

        >>> print(f"This is the secret as string: {s}")
        This is the secret as string: 4e738ca5563c06cfd0018299933d58db1dd8bf97f6973dc99bf6cdc64b5550bd

        >>> print(f"But we can see the actual value: {s.revealed!r}")
        But we can see the actual value: 's3cr3t'

        # Deviating from what we'd ususally expect from `repr`, this deliberately does not show the actual value:
        >>> s.revealed in repr(s)
        False

    """

    revealed: str
    source: str
    id: str

    def _hash(self) -> str:
        return hashlib.sha256(self.revealed.encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        return self._hash()

    def __repr__(self) -> str:
        """*UNSTABLE* Masks the actual value of the secret

        This deliberately breaks the semantics of the `repr` function.
        The exact format of this string may change.
        """
        # The backend uses the `repr` function (via pprint) to create a hash of the agent configuration,
        # so make sure to not return something constant here. Otherwise a changed secret will not trigger
        # a rebake.
        # Worse: In the bakery backend we try to `literal_eval` the resulting string,
        # in oder to render the configuration to the user.
        # As a result, the repr here needs to be evalable, and be compatible with the password model
        # that the backend uses to render passwords in the UI.
        return repr(("cmk_postprocessed", self.source, (self.id, self._hash())))
