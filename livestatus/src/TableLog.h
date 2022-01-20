// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableLog_h
#define TableLog_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <functional>
#include <memory>
#include <string>

#include "Logfile.h"
#include "Table.h"
#include "contact_fwd.h"
class Column;
class LogCache;
class LogEntry;
class LogFiles;
class MonitoringCore;
class Query;
class Row;

class LogFilter {
public:
    size_t max_lines_per_logfile;
    unsigned classmask;
    std::chrono::system_clock::time_point since;
    std::chrono::system_clock::time_point until;
};

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

    static LogFilter constructFilter(Query *query,
                                     size_t max_lines_per_logfile);
    static void processLogFiles(
        const std::function<bool(const LogEntry &)> &processLogEntry,
        const LogFiles &log_files, const LogFilter &log_filter);
    static bool processLogEntries(
        const std::function<bool(const LogEntry &)> &processLogEntry,
        const Logfile::map_type *entries, const LogFilter &log_filter);
};

#endif  // TableLog_h
