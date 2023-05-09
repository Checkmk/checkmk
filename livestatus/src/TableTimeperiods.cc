// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableTimeperiods.h"

#include <memory>

#include "BoolColumn.h"
#include "Column.h"
#include "NagiosGlobals.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "TimeperiodsCache.h"
#include "nagios.h"

TableTimeperiods::TableTimeperiods(MonitoringCore* mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<timeperiod>>(
        "name", "The name of the timeperiod", offsets,
        [](const timeperiod& tp) { return tp.name; }));
    addColumn(std::make_unique<StringColumn<timeperiod>>(
        "alias", "The alias of the timeperiod", offsets,
        [](const timeperiod& tp) { return tp.alias; }));
    // unknown timeperiod is assumed to be 24X7
    addColumn(std::make_unique<BoolColumn<timeperiod, true>>(
        "in", "Wether we are currently in this period (0/1)", offsets,
        [](const timeperiod& tp) {
            // NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
            extern TimeperiodsCache* g_timeperiods_cache;
            return g_timeperiods_cache->inTimeperiod(&tp);
        }));
    // TODO(mk): add days and exceptions
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query* query) {
    for (const timeperiod* tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (!query->processDataset(Row{tp})) {
            break;
        }
    }
}
