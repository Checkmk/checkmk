// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableTimeperiods.h"
#include <cstdint>
#include <memory>
#include "Column.h"
#include "IntLambdaColumn.h"
#include "Query.h"
#include "Row.h"
#include "StringLambdaColumn.h"
#include "TimeperiodsCache.h"
#include "nagios.h"

namespace {
class TimePeriodRow : TableTimeperiods::IRow {
public:
    explicit TimePeriodRow(const timeperiod* tp) : tp_{tp} {}
    [[nodiscard]] const timeperiod* getTimePeriod() const override {
        return tp_;
    }

private:
    const timeperiod* tp_;
};
}  // namespace

struct TimePeriodValue {
    std::int32_t operator()(Row /*row*/);
};

std::int32_t TimePeriodValue::operator()(Row row) {
    extern TimeperiodsCache* g_timeperiods_cache;
    if (auto tp = row.rawData<TableTimeperiods::IRow>()->getTimePeriod()) {
        return g_timeperiods_cache->inTimeperiod(tp) ? 1 : 0;
    }
    return 1;  // unknown timeperiod is assumed to be 24X7
}

TableTimeperiods::TableTimeperiods(MonitoringCore* mc) : Table(mc) {
    addColumn(std::make_unique<StringLambdaColumn>(
        "name", "The name of the timeperiod", [](Row row) -> std::string {
            if (auto tp = row.rawData<IRow>()->getTimePeriod()) {
                return tp->name;
            }
            return {};
        }));
    addColumn(std::make_unique<StringLambdaColumn>(
        "alias", "The alias of the timeperiod", [](Row row) -> std::string {
            if (auto tp = row.rawData<IRow>()->getTimePeriod()) {
                return tp->alias;
            }
            return {};
        }));
    addColumn(std::make_unique<IntLambdaColumn>(
        "in", "Wether we are currently in this period (0/1)",
        TimePeriodValue{}));
    // TODO(mk): add days and exceptions
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query* query) {
    for (timeperiod* tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        auto r = TimePeriodRow{tp};
        if (!query->processDataset(Row{&r})) {
            break;
        }
    }
}
