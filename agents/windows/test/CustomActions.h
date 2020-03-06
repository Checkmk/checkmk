// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include <tuple>
#include "gmock/gmock.h"
#include "gtest/gtest.h"

ACTION_TEMPLATE(SetCharBuffer, HAS_1_TEMPLATE_PARAMS(unsigned, uIndex),
                AND_1_VALUE_PARAMS(data)) {
    // Courtesy of Microsoft: A function takes a char** param
    // but is declared as taking char* (>sigh<)
    *reinterpret_cast<char **>(std::get<uIndex>(args)) = data;
}
