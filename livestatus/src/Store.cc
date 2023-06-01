// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Store.h"

#include <utility>

#include "livestatus/ICore.h"
#include "livestatus/OutputBuffer.h"
#include "livestatus/Query.h"
#include "livestatus/Table.h"

#ifdef CMC
#include "livestatus/ChronoUtils.h"
#include "livestatus/Logger.h"
#endif

Store::Store(ICore *mc)
    : _mc(mc)
    , _log_cache(mc)
#ifdef CMC
    , _table_cached_statehist(mc)
#endif
    , _table_columns(mc)
    , _table_commands(mc)
    , _table_comments(mc)
    , _table_contactgroups(mc)
    , _table_contacts(mc)
    , _table_crash_reports(mc)
    , _table_downtimes(mc)
    , _table_eventconsoleevents(mc)
    , _table_eventconsolehistory(mc)
    , _table_eventconsolereplication(mc)
    , _table_eventconsolerules(mc)
    , _table_eventconsolestatus(mc)
    , _table_hostgroups(mc)
    , _table_hosts(mc)
    , _table_hostsbygroup(mc)
    , _table_labels(mc)
    , _table_log(mc, &_log_cache)
    , _table_servicegroups(mc)
    , _table_services(mc)
    , _table_servicesbygroup(mc)
    , _table_servicesbyhostgroup(mc)
    , _table_statehistory(mc, &_log_cache)
    , _table_status(mc)
    , _table_timeperiods(mc)
    , _table_dummy(mc) {
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

Logger *Store::logger() const { return _mc->loggerLivestatus(); }

size_t Store::numCachedLogMessages() {
    return _log_cache.numCachedLogMessages();
}

bool Store::answerGetRequest(const std::list<std::string> &lines,
                             OutputBuffer &output,
                             const std::string &tablename) {
    return Query{lines,
                 findTable(output, tablename),
                 _mc->dataEncoding(),
                 _mc->maxResponseSize(),
                 output,
                 logger()}
        .process();
}

void Store::addTable(Table &table) {
    _tables.emplace(table.name(), &table);
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

#ifdef CMC

// Depending on wether the state history cache is enabled or not a different
// implementation of the statehist table is being used. This can be switched
// dynamically.
void Store::switchStatehistTable(
    std::optional<std::chrono::seconds> cache_horizon, Logger *logger) {
    if (cache_horizon) {
        addTable(_table_cached_statehist);
        Notice(logger) << "using state history cache with a horizon of "
                       << (mk::ticks<std::chrono::hours>(*cache_horizon) / 24)
                       << " days";
    } else {
        addTable(_table_statehistory);
        Notice(logger) << "state history cache will not be used";
    }
}

#endif
