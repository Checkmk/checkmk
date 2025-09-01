// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/Store.h"

#include <functional>
#include <memory>
#include <utility>

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/ParsedQuery.h"
#include "livestatus/Query.h"
#include "livestatus/Table.h"

Store::Store(Logger *logger)
    : logger_{logger}
    , _log_cache{logger}
    , _table_log{&_log_cache}
    , _table_statehistory{&_log_cache} {
    addTable(_table_columns);
    addTable(_table_commands);
    addTable(_table_comments);
    addTable(_table_contactgroups);
    addTable(_table_contacts);
    addTable(_table_crash_reports);
    addTable(_table_downtimes);
    addTable(_table_eventconsoleevents);
    addTable(_table_eventconsolehistory);
    addTable(_table_eventconsolereplication);
    addTable(_table_eventconsolerules);
    addTable(_table_eventconsolestatus);
    addTable(_table_hostgroups);
    addTable(_table_hosts);
    addTable(_table_hostsbygroup);
    addTable(_table_labels);
    addTable(_table_log);
    addTable(_table_servicegroups);
    addTable(_table_services);
    addTable(_table_servicesbygroup);
    addTable(_table_servicesbyhostgroup);
    addTable(_table_statehistory);
    addTable(_table_status);
    addTable(_table_timeperiods);
}

Logger *Store::logger() const { return logger_; }

size_t Store::numCachedLogMessages(const ICore &core) {
    return _log_cache.apply(
        core.paths()->history_file(), core.paths()->history_archive_directory(),
        core.last_logfile_rotation(),
        [](const LogFiles & /*log_files*/, size_t num_cached_log_messages) {
            return num_cached_log_messages;
        });
}

bool Store::answerGetRequest(const ICore &core,
                             const std::vector<std::string> &lines,
                             OutputBuffer &output,
                             const std::string &tablename) {
    auto &table = findTable(output, tablename);
    return Query{ParsedQuery{lines, [&table]() { return table.allColumns(); },
                             [&table, &core](const auto &colname) {
                                 return table.column(colname, core);
                             }},
                 table, core, output}
        .process();
}

void Store::addTable(Table &table) {
    _tables[table.name()] = &table;
    _table_columns.addTable(table);
}

Table &Store::findTable(OutputBuffer &output, const std::string &name) {
    // NOTE: Even with an invalid table name we continue, so we can parse
    // headers, especially ResponseHeader.
    if (name.empty()) {
        output.setError(OutputBuffer::ResponseCode::invalid_request,
                        "Invalid GET request, missing table name");
        return _table_dummy;
    }
    auto it = _tables.find(name);
    if (it == _tables.end()) {
        output.setError(OutputBuffer::ResponseCode::not_found,
                        "Invalid GET request, no such table '" + name + "'");
        return _table_dummy;
    }
    return *it->second;
}
