#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import FormSpec

type FolderChoices = Callable[[], Sequence[tuple[str, str]]]


@dataclass(frozen=True)
class ConnectorParametersSpec:
    """Specification of a DCD connector's GUI parameters.

    Instances of this class will only be picked up by Checkmk if their names
    start with ``connector_params_``.

    The ``name`` must match the corresponding :class:`ConnectorSpec` name so that the
    GUI can associate the parameters with the correct connector.

    ``form_spec`` builds the parameter form. It receives the folder choices of the
    request, so a folder choice in the form lists the folders of that request's tree.
    """

    name: str
    title: str
    description: str
    form_spec: Callable[[FolderChoices], FormSpec]  # type: ignore[type-arg]
