// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CustomVarsNamesColumn.h"

#include <algorithm>
#include <iterator>
#include <unordered_map>

#include "MonitoringCore.h"
#include "Row.h"

#ifndef CMC
// TODO(sp) Why on earth is "contact_fwd.h" not enough???
#include "nagios.h"
#endif

std::vector<std::string> CustomVarsNamesColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> names;
    if (const auto *p = columnData<void>(row)) {
        auto attrs = _mc->customAttributes(p, _kind);
        std::transform(attrs.begin(), attrs.end(), std::back_inserter(names),
                       [](const auto &entry) { return entry.first; });
    }
    return names;
}
