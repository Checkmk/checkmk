// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
