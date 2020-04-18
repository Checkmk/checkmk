// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CustomTimeperiodColumn.h"
#include <unordered_map>
#include "MonitoringCore.h"
#include "Row.h"
#include "TimeperiodsCache.h"

extern TimeperiodsCache *g_timeperiods_cache;

// Get the name of a timeperiod from a custom variable and lookup the current
// state of that period
int32_t CustomTimeperiodColumn::getValue(
    Row row, const contact * /* auth_user */) const {
    if (auto p = columnData<void>(row)) {
        auto attrs = _mc->customAttributes(p, AttributeKind::custom_variables);
        auto it = attrs.find(_varname);
        if (it != attrs.end()) {
            return static_cast<int32_t>(
                g_timeperiods_cache->inTimeperiod(it->second));
        }
    }
    return 1;  // assume 24X7
}
