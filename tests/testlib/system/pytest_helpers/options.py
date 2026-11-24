#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Command line options of the cmk_package plugin and the environment variables behind them."""

from typing import Final

ARG_EDITION_CMK: Final[str] = "--cmk-edition"
ARG_VERSION_CMK: Final[str] = "--cmk-version"
ARG_REUSE: Final[str] = "--reuse"
ARG_NO_CLEANUP: Final[str] = "--no-cleanup"
ENV_VAR_EDITION: Final[str] = "EDITION"
ENV_VAR_VERSION: Final[str] = "VERSION"
ENV_VAR_REUSE: Final[str] = "REUSE"
ENV_VAR_CLEANUP: Final[str] = "CLEANUP"
