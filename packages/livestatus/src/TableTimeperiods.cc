// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableTimeperiods.h"

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"

using row_type = ITimeperiod;

// TODO(sp) This shouldn't live here...
namespace column::detail {
template <>
std::string serialize(const std::chrono::system_clock::time_point &t) {
    return std::to_string(std::chrono::system_clock::to_time_t(t));
}
}  // namespace column::detail

TableTimeperiods::TableTimeperiods() {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<row_type>>(
        "name", "The name of the timeperiod", offsets,
        [](const row_type &row) { return row.name(); }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "alias", "The alias of the timeperiod", offsets,
        [](const row_type &row) { return row.alias(); }));
    // unknown timeperiod is assumed to be 24X7
    addColumn(std::make_unique<BoolColumn<row_type, true>>(
        "in", "Wether we are currently in this period (0/1)", offsets,
        [](const row_type &row) { return row.isActive(); }));
    addColumn(std::make_unique<
              ListColumn<row_type, std::chrono::system_clock::time_point>>(
        "transitions",
        "The list of future transitions of the timeperiod (only CMC)", offsets,
        [](const row_type &row, std::chrono::seconds /*timezone_offset*/) {
            return row.transitions({});
        }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "num_transitions",
        "The total number of computed transitions from 0->1 or 1->0", offsets,
        [](const row_type &row) { return row.numTransitions(); }));
    addColumn(std::make_unique<IntColumn<row_type>>(
        "next_transition_id", "The index of the next transition", offsets,
        [](const row_type &row) { return row.nextTransitionId(); }));
    addColumn(std::make_unique<TimeColumn<row_type>>(
        "next_transition",
        "The time of the next transition. 0 if there is no further transition.",
        offsets, [](const row_type &row) { return row.nextTransitionTime(); }));
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query &query, const User & /*user*/,
                                   const ICore &core) {
    core.all_of_timeperiods([&query](const row_type &row) {
        return query.processDataset(Row{&row});
    });
}
