// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableLog_h
#define TableLog_h

#include "config.h"  // IWYU pragma: keep

#include <cstddef>
#include <memory>
#include <string>

#include "LogCache.h"
#include "Table.h"
class Column;
class MonitoringCore;
class Query;
class User;

class TableLog : public Table {
public:
    TableLog(MonitoringCore *mc, LogCache *log_cache);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user) override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;

private:
    LogCache *_log_cache;

    static LogFilter constructFilter(Query &query,
                                     size_t max_lines_per_logfile);
};

#endif  // TableLog_h
