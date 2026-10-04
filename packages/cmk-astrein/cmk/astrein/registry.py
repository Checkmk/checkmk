#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.astrein.checkers.abcmeta_metaclass import ABCMetaMetaclassChecker
from cmk.astrein.checkers.argparse_nargs import ArgparseNargsChecker
from cmk.astrein.checkers.conftest_import import ConftestImportChecker
from cmk.astrein.checkers.html_debug import HTMLDebugChecker
from cmk.astrein.checkers.http_status_literal import HTTPStatusLiteralChecker
from cmk.astrein.checkers.key_size_unit_test import KeySizeUnitTestChecker
from cmk.astrein.checkers.localization import LocalizationChecker
from cmk.astrein.checkers.localization_named_placeholder import LocalizationNamedPlaceholderChecker
from cmk.astrein.checkers.logging_formatter import LoggingFormatterChecker
from cmk.astrein.checkers.logging_named_placeholder import LoggingNamedPlaceholderChecker
from cmk.astrein.checkers.module_layers.checker import ModuleLayersChecker
from cmk.astrein.checkers.pillow_import import PillowImportChecker
from cmk.astrein.checkers.pydantic_type_adapter import PydanticTypeAdapterChecker
from cmk.astrein.checkers.request_input import RequestValidatedInputChecker
from cmk.astrein.checkers.tarfile_open_read import TarfileOpenReadChecker
from cmk.astrein.engine import ENGINE_SUMMARIES
from cmk.astrein.framework import ASTVisitorChecker

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
        **ENGINE_SUMMARIES,
    }
