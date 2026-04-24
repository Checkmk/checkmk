#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema, CoreSchema

from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.licensing.basics.features import FeatureName
from cmk.licensing.registry import is_feature_enabled
from cmk.utils import paths


@dataclass(kw_only=True, slots=True)
class RestrictFeatures:
    """Validate that a field is only available when a specific license feature is enabled.

    The field's description should document the feature requirement manually."""

    required_if_supported: bool = False
    feature_name: FeatureName
    which_field: str

    def _validate_features(self, value: object) -> object:
        if is_feature_enabled(paths.omd_root, self.feature_name):
            if self.required_if_supported and isinstance(value, ApiOmitted):
                raise ValueError(f"The {self.which_field} field is required with this license")
        elif not isinstance(value, ApiOmitted):
            raise ValueError(f"The {self.which_field} field is not supported by this license")
        return value

    def __get_pydantic_core_schema__(
        self, source_type: CoreSchema, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            self._validate_features, handler(source_type)
        )
