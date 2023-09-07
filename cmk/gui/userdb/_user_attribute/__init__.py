#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._custom_attributes import register_custom_user_attributes as register_custom_user_attributes
from ._custom_attributes import (
    update_config_based_user_attributes as update_config_based_user_attributes,
)
