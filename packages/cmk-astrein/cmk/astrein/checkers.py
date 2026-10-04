#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.astrein.checker_argparse_nargs import ArgparseNargsChecker
from cmk.astrein.checker_http_status import HTTPStatusLiteralChecker
from cmk.astrein.checker_key_size import KeySizeUnitTestChecker
from cmk.astrein.checker_localization import (
    LocalizationChecker,
    LocalizationNamedPlaceholderChecker,
)
from cmk.astrein.checker_logging_formatter import LoggingFormatterChecker
from cmk.astrein.checker_module_layers import ModuleLayersChecker
from cmk.astrein.checker_request_input import RequestValidatedInputChecker
from cmk.astrein.checker_simple_patterns import (
    ABCMetaMetaclassChecker,
    ConftestImportChecker,
    HTMLDebugChecker,
    LoggingNamedPlaceholderChecker,
    PillowImportChecker,
    PydanticTypeAdapterChecker,
    TarfileOpenReadChecker,
)
from cmk.astrein.framework import ASTVisitorChecker, FRAMEWORK_SUMMARIES

ALL_CHECKERS: Final[Sequence[type[ASTVisitorChecker]]] = (
    ABCMetaMetaclassChecker,
    ArgparseNargsChecker,
    ConftestImportChecker,
    HTMLDebugChecker,
    HTTPStatusLiteralChecker,
    KeySizeUnitTestChecker,
    LocalizationChecker,
    LocalizationNamedPlaceholderChecker,
    LoggingFormatterChecker,
    LoggingNamedPlaceholderChecker,
    ModuleLayersChecker,
    PillowImportChecker,
    PydanticTypeAdapterChecker,
    RequestValidatedInputChecker,
    TarfileOpenReadChecker,
)


def all_checkers() -> dict[str, type[ASTVisitorChecker]]:
    return {checker.checker_id: checker for checker in ALL_CHECKERS}


def all_summaries() -> Mapping[str, str]:
    return {
        **{checker.checker_id: checker.summary for checker in ALL_CHECKERS},
        **FRAMEWORK_SUMMARIES,
    }
