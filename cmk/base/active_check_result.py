#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Normalization of an active check's raw result into a monitoring state.

An active check yields a Nagios exit code and the plugin's stdout. Two paths
produce that pair: the site-local run (``subprocess``) and the relay run (a
decoded ``checkhelper`` frame). Both funnel through :func:`normalize_active_check_result`
so a given check reports the same state and output wherever it ran.

This lives in ``cmk.base`` on purpose: local active checks run in every edition,
so the shared seam must be community code. The relay-side frame *decode*
(``CheckhelperFrame`` in the enterprise ``cmk.check_helper_protocol``) returns raw
pieces; the caller composes the two (decode, then normalize) rather than the
decoder depending on this module.
"""

from __future__ import annotations

from typing import Final

from cmk.checkengine.submitters import ServiceDetails, ServiceState

_NAGIOS_STATES: Final = frozenset({0, 1, 2})
_UNKNOWN_STATE: Final[ServiceState] = 3


def normalize_active_check_result(
    exit_code: int, raw_output: str
) -> tuple[ServiceState, ServiceDetails]:
    """Map an active check's ``(exit code, raw stdout)`` to a ``(state, output)`` pair.

    * The state is the exit code when it is a Nagios state (``0``/``1``/``2``); any
      other code -- e.g. ``127`` ("command not found") or ``126`` ("not
      executable") -- becomes UNKNOWN (``3``).
    * The output is the text before the first ``|`` (performance data is dropped),
      trimmed of surrounding whitespace.
    """
    state: ServiceState = exit_code if exit_code in _NAGIOS_STATES else _UNKNOWN_STATE
    output: ServiceDetails = raw_output.split("|", 1)[0].strip()
    return state, output
