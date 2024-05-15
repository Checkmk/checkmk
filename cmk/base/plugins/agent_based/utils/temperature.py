#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   Neither this file nor what is imported below are a public API. The contained        #
#   objects and their signature can change at any time without warning (except for      #
#   this one).                                                                          #
#                                                                                       #
#   We are adding this nevertheless (for now!), because some very popular MKPs are      #
#   relying on it, and we want our users to experience a smoother upgrade.              #
#   However, these kind of courtesies are not sustainable.                              #
#                                                                                       #
#   If you are using these functions, please include a copy of them in your MKP.        #
#   That way your MKP will not break inadvertedly.                                      #
#                                                                                       #
#########################################################################################

# pylint: disable=unused-import

# NOTE: we have no idea what exactly is in use.
# Just import everything that is not explicitly marked private.

from cmk.plugins.lib.temperature import (
    celsius_to_fahrenheit,
    check_temperature,
    fahrenheit_to_celsius,
    FourLevelsType,
    from_celsius,
    LevelModes,
    LevelsType,
    render_temp,
    StatusType,
    temp_unitsym,
    TempParamDict,
    TempParamType,
    TempUnitType,
    to_celsius,
    TrendComputeDict,
    TwoLevelsType,
)
