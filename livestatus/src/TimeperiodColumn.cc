// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TimeperiodColumn.h"
#include "Row.h"

#ifdef CMC
#include "Timeperiod.h"
#else
#include "TimeperiodsCache.h"
#include "nagios.h"
#endif

int32_t TimeperiodColumn::getValue(Row row,
                                   const contact* /* auth_user */) const {
#ifdef CMC
    if (auto tp = columnData<Timeperiod>(row)) {
        return tp->isActive() ? 1 : 0;
    }
#else
    extern TimeperiodsCache* g_timeperiods_cache;
    if (auto tp = columnData<timeperiod>(row)) {
        return g_timeperiods_cache->inTimeperiod(tp) ? 1 : 0;
    }
#endif
    return 1;  // unknown timeperiod is assumed to be 24X7
}
