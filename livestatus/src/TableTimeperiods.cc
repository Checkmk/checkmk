// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableTimeperiods.h"

#include <chrono>
#include <memory>
#include <vector>

#include "Column.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "TimeColumn.h"
#include "TimeperiodsCache.h"
#include "nagios.h"

// TODO(sp) This shouldn't live here...
namespace column::detail {
template <>
std::string serialize(const std::chrono::system_clock::time_point &t) {
    return std::to_string(std::chrono::system_clock::to_time_t(t));
}
}  // namespace column::detail

TableTimeperiods::TableTimeperiods(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<timeperiod>>(
        "name", "The name of the timeperiod", offsets,
        [](const timeperiod &tp) { return tp.name; }));
    addColumn(std::make_unique<StringColumn<timeperiod>>(
        "alias", "The alias of the timeperiod", offsets,
        [](const timeperiod &tp) { return tp.alias; }));
    // unknown timeperiod is assumed to be 24X7
    addColumn(std::make_unique<BoolColumn<timeperiod, true>>(
        "in", "Wether we are currently in this period (0/1)", offsets,
        [](const timeperiod &tp) {
            // NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
            extern TimeperiodsCache *g_timeperiods_cache;
            return g_timeperiods_cache->inTimeperiod(&tp);
        }));
    // TODO(sp) Dummy columns only, can we do better? Not used anywhere...
    addColumn(std::make_unique<
              ListColumn<timeperiod, std::chrono::system_clock::time_point>>(
        "transitions",
        "The list of future transitions of the timeperiod (only CMC)", offsets,
        [](const timeperiod & /*tp*/,
           std::chrono::seconds /*timezone_offset*/) {
            return std::vector<std::chrono::system_clock::time_point>{};
        }));
    addColumn(std::make_unique<IntColumn<timeperiod>>(
        "num_transitions",
        "The total number of computed transitions from 0->1 or 1->0", offsets,
        [](const timeperiod & /*tp*/) { return 2; }));
    addColumn(std::make_unique<IntColumn<timeperiod>>(
        "next_transition_id", "The index of the next transition", offsets,
        [](const timeperiod & /*tp*/) { return 1; }));
    addColumn(std::make_unique<TimeColumn<timeperiod>>(
        "next_transition",
        "The time of the next transition. 0 if there is no further transition.",
        offsets, [](const timeperiod & /*tp*/) {
            return std::chrono::system_clock::from_time_t(0);
        }));
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query *query) {
    for (const timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (!query->processDataset(Row{tp})) {
            break;
        }
    }
}
