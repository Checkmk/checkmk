// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableLog_h
#define TableLog_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>

#include "Table.h"
#include "contact_fwd.h"
class Column;
class LogCache;
class LogFiles;
class Logfile;
class MonitoringCore;
class Query;
class Row;

class TableLog : public Table {
public:
    TableLog(MonitoringCore *mc, LogCache *log_cache);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, const contact *ctc) const override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;

private:
    LogCache *_log_cache;
    void answerQueryInternal(Query *query, const LogFiles &log_files);
    bool answerQueryReverse(Query *query, Logfile *logfile,
                            unsigned long classmask,
                            std::chrono::system_clock::time_point since,
                            std::chrono::system_clock::time_point until);
};

#endif  // TableLog_h
