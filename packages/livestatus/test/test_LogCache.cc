// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <string>
#include <vector>

#include "DummyMonitoringCore.h"
#include "gtest/gtest.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logger.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Query.h"
#include "livestatus/TableLog.h"

namespace {
class LoggingCore : public DummyMonitoringCore {
public:
    [[nodiscard]] Logger *loggerLivestatus() const override {
        return Logger::getLogger("test");
    }
};

LogPeriod logPeriodFor(const std::vector<std::string> &query_lines) {
    const LoggingCore core;
    LogCache log_cache{core.loggerLivestatus()};
    TableLog table{&log_cache};
    OutputBuffer output{-1, [] { return false; }, core.loggerLivestatus()};
    const Query query{
        ParsedQuery{query_lines, [&table] { return table.allColumns(); },
                    [&table, &core](const auto &colname) {
                        return table.column(colname, core);
                    }},
        table, core, output};
    return LogPeriod::make(query);
}
}  // namespace

TEST(LogPeriodTest, EndsAfterTheLeastUpperBound) {
    EXPECT_EQ(logPeriodFor({"Filter: time <= 1000"}).until,
              std::chrono::system_clock::from_time_t(1001));
}

TEST(LogPeriodTest, EndsAfterTheMaximumLeastUpperBound) {
    EXPECT_EQ(logPeriodFor({"Filter: time <= 2147483647"}).until,
              std::chrono::system_clock::from_time_t(2147483648));
}
