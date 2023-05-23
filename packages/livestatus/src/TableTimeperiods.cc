// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableTimeperiods.h"

#include <chrono>
#include <cstdint>
#include <memory>
#include <variant>  // IWYU pragma: keep
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

// TODO(sp) This shouldn't live here...
namespace column::detail {
template <>
std::string serialize(const std::chrono::system_clock::time_point &t) {
    return std::to_string(std::chrono::system_clock::to_time_t(t));
}
}  // namespace column::detail

TableTimeperiods::TableTimeperiods(ICore *mc) : Table(mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<ITimeperiod>>(
        "name", "The name of the timeperiod", offsets,
        [](const ITimeperiod &tp) { return tp.name(); }));
    addColumn(std::make_unique<StringColumn<ITimeperiod>>(
        "alias", "The alias of the timeperiod", offsets,
        [](const ITimeperiod &tp) { return tp.alias(); }));
    // unknown timeperiod is assumed to be 24X7
    addColumn(std::make_unique<BoolColumn<ITimeperiod, true>>(
        "in", "Wether we are currently in this period (0/1)", offsets,
        [](const ITimeperiod &tp) { return tp.isActive(); }));
    addColumn(std::make_unique<
              ListColumn<ITimeperiod, std::chrono::system_clock::time_point>>(
        "transitions",
        "The list of future transitions of the timeperiod (only CMC)", offsets,
        [](const ITimeperiod &tp, std::chrono::seconds /*timezone_offset*/) {
            return tp.transitions({});
        }));
    addColumn(std::make_unique<IntColumn<ITimeperiod>>(
        "num_transitions",
        "The total number of computed transitions from 0->1 or 1->0", offsets,
        [](const ITimeperiod &tp) { return tp.numTransitions(); }));
    addColumn(std::make_unique<IntColumn<ITimeperiod>>(
        "next_transition_id", "The index of the next transition", offsets,
        [](const ITimeperiod &tp) { return tp.nextTransitionId(); }));
    addColumn(std::make_unique<TimeColumn<ITimeperiod>>(
        "next_transition",
        "The time of the next transition. 0 if there is no further transition.",
        offsets,
        [](const ITimeperiod &tp) { return tp.nextTransitionTime(); }));
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query &query, const User & /*user*/) {
    core()->all_of_timeperiods([&query](const ITimeperiod &r) {
        return query.processDataset(Row{&r});
    });
}
