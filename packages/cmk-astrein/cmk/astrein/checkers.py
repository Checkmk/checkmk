#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
    HTMLDebugChecker,
    LoggingNamedPlaceholderChecker,
    PillowImportChecker,
    PydanticTypeAdapterChecker,
    TarfileOpenReadChecker,
)
from cmk.astrein.framework import ASTVisitorChecker


def all_checkers() -> dict[str, type[ASTVisitorChecker]]:
    return {
        "abcmeta-metaclass": ABCMetaMetaclassChecker,
        "html-debug": HTMLDebugChecker,
        "key-size-unit-test": KeySizeUnitTestChecker,
        "localization": LocalizationChecker,
        "localization-named-placeholder": LocalizationNamedPlaceholderChecker,
        "logging-formatter": LoggingFormatterChecker,
        "logging-named-placeholder": LoggingNamedPlaceholderChecker,
        "module-layers": ModuleLayersChecker,
        "pillow-import": PillowImportChecker,
        "pydantic-type-adapter": PydanticTypeAdapterChecker,
        "tarfile-open-read": TarfileOpenReadChecker,
        "use-request-getvalidatedinputtype": RequestValidatedInputChecker,
    }
