#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class TransformDataForLegacyFormatOrRecomposeFunction(FormSpec[object]):
    """DO NOT USE THIS CLASS, UNLESS YOU HAVE A GOOD REASON!
    It was introduced to transform ugly formatted data from disk to a format that is more
    suitable for the FormSpecs. It should only be used for
     - legacy reasons if the old data format cannot be cleaned up within a reasonable time
       The correct way to transform legacy data is to use a migration function in the FormSpec.
     - recompose functions where a formspec is shown as a composition of other form specs


    This form spec is used to transform a value from one format to another.
    It does -not- add any extra logic, layout or title
    The value is only transformed for RawDiskData
    """

    wrapped_form_spec: FormSpec[Any]
    from_disk: Callable[[object], object]
    to_disk: Callable[[object], object]
