// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetTimeColumn.h"
#include <ctime>
#include "Row.h"

std::chrono::system_clock::time_point OffsetTimeColumn::getRawValue(
    Row row) const {
    if (auto p = columnData<time_t>(row)) {
        return std::chrono::system_clock::from_time_t(*p);
    }
    return {};
}
