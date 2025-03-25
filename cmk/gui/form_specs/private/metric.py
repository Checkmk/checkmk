#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.gui.form_specs.private.string_autocompleter import StringAutocompleter


@dataclass(frozen=True, kw_only=True)
class MetricExtended(StringAutocompleter):
    # This class only exists to use a custom visitor that adds
    # two additional fields to the string auto completer form spec.
    pass
