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

#include "TableStateHistory.h"
#include <ctime>
#include <deque>
#include <memory>
#include <mutex>
#include <ostream>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>
#include "Column.h"
#include "ColumnFilter.h"
#include "Filter.h"
#include "FilterVisitor.h"
#include "HostServiceState.h"
#include "LogEntry.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetSStringColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "Row.h"
#include "StringUtils.h"
#include "TableHosts.h"
#include "TableServices.h"
class NegatingFilter;
class VariadicFilter;

#ifdef CMC
#include "Host.h"
#include "Service.h"
#include "Timeperiod.h"
#include "cmc.h"
#define STATE_OK 0
#define STATE_WARNING 1
#define STATE_CRITICAL 2
#define STATE_UNKNOWN 3
#else
#include "auth.h"
#include "nagios.h"
#endif

using mk::starts_with;
using std::deque;
using std::lock_guard;
using std::make_unique;
using std::map;
using std::mutex;
using std::set;
using std::shared_ptr;
using std::string;

namespace {
constexpr unsigned classmask_statehist =
    (1u << static_cast<int>(LogEntry::Class::alert)) |    //
    (1u << static_cast<int>(LogEntry::Class::program)) |  //
    (1u << static_cast<int>(LogEntry::Class::state)) |    //
    (1u << static_cast<int>(LogEntry::Class::text));
}  // namespace

#ifndef CMC
namespace {
string getCustomVariable(customvariablesmember *cvm, const string &name) {
    for (; cvm != nullptr; cvm = cvm->next) {
        if (cvm->variable_name == name) {
            return cvm->variable_value == nullptr ? "" : cvm->variable_value;
        }
    }
    return "";
}
}  // namespace
#endif

TableStateHistory::TableStateHistory(MonitoringCore *mc, LogCache *log_cache)
    : Table(mc), _log_cache(log_cache) {
    addColumn(make_unique<OffsetTimeColumn>(
        "time", "Time of the log event (seconds since 1/1/1970)",
        DANGEROUS_OFFSETOF(HostServiceState, _time), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "lineno", "The number of the line in the log file",
        DANGEROUS_OFFSETOF(HostServiceState, _lineno), -1, -1, -1));
    addColumn(make_unique<OffsetTimeColumn>(
        "from", "Start time of state (seconds since 1/1/1970)",
        DANGEROUS_OFFSETOF(HostServiceState, _from), -1, -1, -1));
    addColumn(make_unique<OffsetTimeColumn>(
        "until", "End time of state (seconds since 1/1/1970)",
        DANGEROUS_OFFSETOF(HostServiceState, _until), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "duration", "Duration of state (until - from)",
        DANGEROUS_OFFSETOF(HostServiceState, _duration), -1, -1, -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part", "Duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "state",
        "The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)",
        DANGEROUS_OFFSETOF(HostServiceState, _state), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "host_down", "Shows if the host of this service is down",
        DANGEROUS_OFFSETOF(HostServiceState, _host_down), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "in_downtime", "Shows if the host or service is in downtime",
        DANGEROUS_OFFSETOF(HostServiceState, _in_downtime), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "in_host_downtime", "Shows if the host of this service is in downtime",
        DANGEROUS_OFFSETOF(HostServiceState, _in_host_downtime), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "is_flapping", "Shows if the host or service is flapping",
        DANGEROUS_OFFSETOF(HostServiceState, _is_flapping), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "in_notification_period",
        "Shows if the host or service is within its notification period",
        DANGEROUS_OFFSETOF(HostServiceState, _in_notification_period), -1, -1,
        -1));
    addColumn(make_unique<OffsetStringColumn>(
        "notification_period",
        "The notification period of the host or service in question",
        DANGEROUS_OFFSETOF(HostServiceState, _notification_period), -1, -1,
        -1));
    addColumn(make_unique<OffsetIntColumn>(
        "in_service_period",
        "Shows if the host or service is within its service period",
        DANGEROUS_OFFSETOF(HostServiceState, _in_service_period), -1, -1, -1));
    addColumn(make_unique<OffsetSStringColumn>(
        "service_period",
        "The service period of the host or service in question",
        DANGEROUS_OFFSETOF(HostServiceState, _service_period), -1, -1, -1));
    addColumn(make_unique<OffsetSStringColumn>(
        "debug_info", "Debug information",
        DANGEROUS_OFFSETOF(HostServiceState, _debug_info), -1, -1, -1));
    addColumn(make_unique<OffsetSStringColumn>(
        "host_name", "Host name",
        DANGEROUS_OFFSETOF(HostServiceState, _host_name), -1, -1, -1));
    addColumn(make_unique<OffsetSStringColumn>(
        "service_description", "Description of the service",
        DANGEROUS_OFFSETOF(HostServiceState, _service_description), -1, -1,
        -1));
    addColumn(make_unique<OffsetSStringColumn>(
        "log_output", "Logfile output relevant for this state",
        DANGEROUS_OFFSETOF(HostServiceState, _log_output), -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "duration_ok", "OK duration of state ( until - from )",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_state_OK), -1, -1, -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part_ok", "OK duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part_OK), -1, -1, -1));

    addColumn(make_unique<OffsetIntColumn>(
        "duration_warning", "WARNING duration of state (until - from)",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_state_WARNING), -1, -1,
        -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part_warning",
        "WARNING duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part_WARNING), -1, -1,
        -1));

    addColumn(make_unique<OffsetIntColumn>(
        "duration_critical", "CRITICAL duration of state (until - from)",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_state_CRITICAL), -1, -1,
        -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part_critical",
        "CRITICAL duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part_CRITICAL), -1, -1,
        -1));

    addColumn(make_unique<OffsetIntColumn>(
        "duration_unknown", "UNKNOWN duration of state (until - from)",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_state_UNKNOWN), -1, -1,
        -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part_unknown",
        "UNKNOWN duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part_UNKNOWN), -1, -1,
        -1));

    addColumn(make_unique<OffsetIntColumn>(
        "duration_unmonitored", "UNMONITORED duration of state (until - from)",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_state_UNMONITORED), -1,
        -1, -1));
    addColumn(make_unique<OffsetDoubleColumn>(
        "duration_part_unmonitored",
        "UNMONITORED duration part in regard to the query timeframe",
        DANGEROUS_OFFSETOF(HostServiceState, _duration_part_UNMONITORED), -1,
        -1, -1));

    // join host and service tables
    TableHosts::addColumns(this, mc, "current_host_",
                           DANGEROUS_OFFSETOF(HostServiceState, _host), -1);
    TableServices::addColumns(this, mc, "current_service_",
                              DANGEROUS_OFFSETOF(HostServiceState, _service),
                              false /* no hosts table */);
}

string TableStateHistory::name() const { return "statehist"; }

string TableStateHistory::namePrefix() const { return "statehist_"; }

LogEntry *TableStateHistory::getPreviousLogentry() {
    while (_it_entries == _entries->begin()) {
        // open previous logfile
        if (_it_logs == _log_cache->logfiles()->begin()) {
            return nullptr;
        }
        --_it_logs;
        _entries = _it_logs->second->getEntriesFromQuery(
            _query, _log_cache, _since, _until, classmask_statehist);
        _it_entries = _entries->end();
    }

    return (--_it_entries)->second;
}

LogEntry *TableStateHistory::getNextLogentry() {
    if (_it_entries != _entries->end()) {
        ++_it_entries;
    }

    while (_it_entries == _entries->end()) {
        auto it_logs_cpy = _it_logs;
        if (++it_logs_cpy == _log_cache->logfiles()->end()) {
            return nullptr;
        }
        ++_it_logs;
        _entries = _it_logs->second->getEntriesFromQuery(
            _query, _log_cache, _since, _until, classmask_statehist);
        _it_entries = _entries->begin();
    }
    return _it_entries->second;
}

// TODO(sp) IsObjectFilter in TableCachedStatehist recurses into sub-filters,
// while we don't. Is this really intentional?
namespace {
class IsObjectFilter : public FilterVisitor {
public:
    void visit(ColumnFilter &f) override {
        if (_value) {
            auto column_name = f.column()->name();
            _value = starts_with(column_name, string("current_")) ||
                     starts_with(column_name, string("host_")) ||
                     starts_with(column_name, string("service_"));
        }
    }
    void visit(NegatingFilter & /*unused*/) override {}
    void visit(VariadicFilter & /*unused*/) override {}

    bool _value = true;
};

class TimeperiodTransition {
public:
    explicit TimeperiodTransition(const string &str) {
        auto fields = mk::split(str, ';');
        if (fields.size() != 3) {
            throw std::invalid_argument("expected 3 arguments");
        }
        _name = fields[0];
        _from = std::stoi(fields[1]);
        _to = std::stoi(fields[2]);
    }

    string name() const { return _name; }
    int from() const { return _from; }
    int to() const { return _to; }

private:
    string _name;
    int _from;
    int _to;
};
}  // namespace

void TableStateHistory::answerQuery(Query *query) {
    // Create a partial filter, that contains only such filters that
    // check attributes of current hosts and services
    deque<Filter *> object_filter;

    if (core()->stateHistoryFilteringEnabled()) {
        for (const auto &filter : *query->filter()) {
            IsObjectFilter is_obj;
            filter->accept(is_obj);
            if (is_obj._value) {
                object_filter.push_back(filter.get());
            }
        }
    }

    lock_guard<mutex> lg(_log_cache->_lock);
    if (!_log_cache->logCachePreChecks()) {
        return;
    }

    // This flag might be set to true by the return value of processDataset(...)
    _abort_query = false;

    // Keep track of the historic state of services/hosts here
    map<HostServiceKey, HostServiceState *> state_info;

    // Store hosts/services that we have filtered out here
    set<HostServiceKey> object_blacklist;

    _query = query;
    _since = 0;
    _until = time(nullptr) + 1;

    // Optimize time interval for the query. In log querys
    // there should always be a time range in form of one
    // or two filter expressions over time. We use that
    // to limit the number of logfiles we need to scan and
    // to find the optimal entry point into the logfile
    _query->findIntLimits("time", &_since, &_until);
    if (_since == 0) {
        query->invalidRequest(
            "Start of timeframe required. e.g. Filter: time > 1234567890");
        return;
    }

    _query_timeframe = _until - _since - 1;
    if (_query_timeframe == 0) {
        query->invalidRequest("Query timeframe is 0 seconds");
        return;
    }

    // Switch to last logfile (we have at least one)
    _it_logs = _log_cache->logfiles()->end();
    --_it_logs;
    auto newest_log = _it_logs;

    // Now find the log where 'since' starts.
    while (_it_logs != _log_cache->logfiles()->begin() &&
           _it_logs->first >= _since) {
        --_it_logs;  // go back in history
    }

    // Check if 'until' is within these logfiles
    if (_it_logs->first > _until) {
        // All logfiles are too new, invalid timeframe
        // -> No data available. Return empty result.
        return;
    }

    // Determine initial logentry
    LogEntry *entry;
    _entries = _it_logs->second->getEntriesFromQuery(
        query, _log_cache, _since, _until, classmask_statehist);
    if (!_entries->empty() && _it_logs != newest_log) {
        _it_entries = _entries->end();
        // Check last entry. If it's younger than _since -> use this logfile too
        if (--_it_entries != _entries->begin()) {
            entry = _it_entries->second;
            if (entry->_time >= _since) {
                _it_entries = _entries->begin();
            }
        }
    } else {
        _it_entries = _entries->begin();
    }

    // From now on use getPreviousLogentry() / getNextLogentry()
    bool only_update = true;
    bool in_nagios_initial_states = false;

    while (nullptr != (entry = getNextLogentry())) {
        if (_abort_query) {
            break;
        }

        if (entry->_time >= _until) {
            getPreviousLogentry();
            break;
        }
        if (only_update && entry->_time >= _since) {
            // Reached start of query timeframe. From now on let's produce real
            // output. Update _from time of every state entry
            for (auto &it_hst : state_info) {
                it_hst.second->_from = _since;
                it_hst.second->_until = _since;
            }
            only_update = false;
        }

        if (in_nagios_initial_states &&
            !(entry->_type == LogEntryType::state_service_initial ||
              entry->_type == LogEntryType::state_host_initial)) {
            // Set still unknown hosts / services to unmonitored
            for (auto &it_hst : state_info) {
                HostServiceState *hst = it_hst.second;
                if (hst->_may_no_longer_exist) {
                    hst->_has_vanished = true;
                }
            }
            in_nagios_initial_states = false;
        }

        HostServiceKey key = nullptr;
        bool is_service = false;
        switch (entry->_type) {
            case LogEntryType::none:
            case LogEntryType::core_starting:
            case LogEntryType::core_stopping:
            case LogEntryType::log_version:
            case LogEntryType::acknowledge_alert_host:
            case LogEntryType::acknowledge_alert_service:
                break;
            case LogEntryType::alert_service:
            case LogEntryType::state_service:
            case LogEntryType::state_service_initial:
            case LogEntryType::downtime_alert_service:
            case LogEntryType::flapping_service:
                key = entry->_service;
                is_service = true;
            // fall-through
            case LogEntryType::alert_host:
            case LogEntryType::state_host:
            case LogEntryType::state_host_initial:
            case LogEntryType::downtime_alert_host:
            case LogEntryType::flapping_host: {
                if (!is_service) {
                    key = entry->_host;
                }

                if (key == nullptr) {
                    continue;
                }

                if (object_blacklist.find(key) != object_blacklist.end()) {
                    // Host/Service is not needed for this query and has already
                    // been filtered out.
                    continue;
                }

                // Find state object for this host/service
                HostServiceState *state;
                auto it_hst = state_info.find(key);
                if (it_hst == state_info.end()) {
                    // Create state object that we also need for filtering right
                    // now
                    state = new HostServiceState();
                    state->_is_host = entry->_svc_desc.empty();
                    state->_host = entry->_host;
                    state->_service = entry->_service;
#ifdef CMC
                    state->_host_name = entry->_host->name();
                    state->_service_description = entry->_service == nullptr
                                                      ? ""
                                                      : entry->_service->name();
#else
                    state->_host_name = entry->_host->name;
                    state->_service_description =
                        entry->_service == nullptr
                            ? ""
                            : entry->_service->description;
#endif

                    // No state found. Now check if this host/services is
                    // filtered out.  Note: we currently do not filter out hosts
                    // since they might be needed for service states
                    if (!entry->_svc_desc.empty()) {
                        bool filtered_out = false;
                        for (auto filter : object_filter) {
                            if (!filter->accepts(Row(state), query->authUser(),
                                                 query->timezoneOffset())) {
                                filtered_out = true;
                                break;
                            }
                        }

                        if (filtered_out) {
                            object_blacklist.insert(key);
                            delete state;
                            continue;
                        }
                    }

                    // Host/Service relations
                    if (state->_is_host) {
                        for (auto &it_inh : state_info) {
                            if (it_inh.second->_host == state->_host) {
                                state->_services.push_back(it_inh.second);
                            }
                        }
                    } else {
                        auto it_inh = state_info.find(state->_host);
                        if (it_inh != state_info.end()) {
                            it_inh->second->_services.push_back(state);
                        }
                    }

                    // Store this state object for tracking state transitions
                    state_info.emplace(key, state);
                    state->_from = _since;

                    // Get notification period of host/service
                    // If this host/service is no longer availabe in nagios ->
                    // set to ""
                    if (state->_service != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_service->notificationPeriod()->name();
#else
                        auto np = state->_service->notification_period;
                        state->_notification_period = np == nullptr ? "" : np;
#endif
                    } else if (state->_host != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_host->notificationPeriod()->name();
#else
                        auto np = state->_host->notification_period;
                        state->_notification_period = np == nullptr ? "" : np;
#endif
                    } else {
                        state->_notification_period = "";
                    }

                    // Same for service period. For Nagios this is a bit
                    // different, since this is no native field but just a
                    // custom variable
                    if (state->_service != nullptr) {
#ifdef CMC
                        state->_service_period =
                            state->_service->servicePeriod()->name();
#else
                        state->_service_period =
                            getCustomVariable(state->_service->custom_variables,
                                              "SERVICE_PERIOD");
#endif
                    } else if (state->_host != nullptr) {
#ifdef CMC
                        state->_service_period =
                            state->_host->servicePeriod()->name();
#else
                        state->_service_period = getCustomVariable(
                            state->_host->custom_variables, "SERVICE_PERIOD");
#endif
                    } else {
                        state->_service_period = "";
                    }

                    // Determine initial in_notification_period status
                    auto tmp_period =
                        _notification_periods.find(state->_notification_period);
                    if (tmp_period != _notification_periods.end()) {
                        state->_in_notification_period = tmp_period->second;
                    } else {
                        state->_in_notification_period = 1;
                    }

                    // Same for service period
                    tmp_period =
                        _notification_periods.find(state->_service_period);
                    if (tmp_period != _notification_periods.end()) {
                        state->_in_service_period = tmp_period->second;
                    } else {
                        state->_in_service_period = 1;
                    }

                    // If this key is a service try to find its host and apply
                    // its _in_host_downtime and _host_down parameters
                    if (!state->_is_host) {
                        auto my_host = state_info.find(state->_host);
                        if (my_host != state_info.end()) {
                            state->_in_host_downtime =
                                my_host->second->_in_host_downtime;
                            state->_host_down = my_host->second->_host_down;
                        }
                    }

                    // Log UNMONITORED state if this host or service just
                    // appeared within the query timeframe
                    // It gets a grace period of ten minutes (nagios startup)
                    if (!only_update && entry->_time - _since > 60 * 10) {
                        state->_debug_info = "UNMONITORED ";
                        state->_state = -1;
                    }
                } else {
                    state = it_hst->second;
                }

                int state_changed =
                    updateHostServiceState(query, entry, state, only_update);
                // Host downtime or state changes also affect its services
                if (entry->_type == LogEntryType::alert_host ||
                    entry->_type == LogEntryType::state_host ||
                    entry->_type == LogEntryType::downtime_alert_host) {
                    if (state_changed != 0) {
                        for (auto &_service : state->_services) {
                            updateHostServiceState(query, entry, _service,
                                                   only_update);
                        }
                    }
                }
                break;
            }
            case LogEntryType::timeperiod_transition: {
                try {
                    TimeperiodTransition tpt(entry->_options);
                    _notification_periods[tpt.name()] = tpt.to();
                    for (auto &it_hst : state_info) {
                        updateHostServiceState(query, entry, it_hst.second,
                                               only_update);
                    }
                } catch (const std::logic_error &e) {
                    Warning(logger())
                        << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                        << entry->_complete;
                }
                break;
            }
            case LogEntryType::log_initial_states: {
                // This feature is only available if log_initial_states is set
                // to 1. If log_initial_states is set, each nagios startup logs
                // the initial states of all known hosts and services. Therefore
                // we can detect if a host is no longer available after a nagios
                // startup. If it still exists an INITIAL HOST/SERVICE state
                // entry will follow up shortly.
                for (auto &it_hst : state_info) {
                    if (!it_hst.second->_has_vanished) {
                        it_hst.second->_last_known_time = entry->_time;
                        it_hst.second->_may_no_longer_exist = true;
                    }
                }
                in_nagios_initial_states = true;
                break;
            }
        }
    }

    // Create final reports
    auto it_hst = state_info.begin();
    if (!_abort_query) {
        while (it_hst != state_info.end()) {
            HostServiceState *hst = it_hst->second;

            // No trace since the last two nagios startup -> host/service has
            // vanished
            if (hst->_may_no_longer_exist) {
                // Log last known state up to nagios restart
                hst->_time = hst->_last_known_time;
                hst->_until = hst->_last_known_time;
                process(query, hst);

                // Set absent state
                hst->_state = -1;
                hst->_until = hst->_time;
                hst->_debug_info = "UNMONITORED";
                hst->_log_output = "";
            }

            hst->_time = _until - 1;
            hst->_until = hst->_time;

            process(query, hst);
            ++it_hst;
        }
    }

    // Cleanup !
    it_hst = state_info.begin();
    while (it_hst != state_info.end()) {
        delete it_hst->second;
        ++it_hst;
    }
    state_info.clear();
    object_blacklist.clear();
}

int TableStateHistory::updateHostServiceState(Query *query,
                                              const LogEntry *entry,
                                              HostServiceState *hs_state,
                                              const bool only_update) {
    int state_changed = 1;

    // Revive host / service if it was unmonitored
    if (entry->_type != LogEntryType::timeperiod_transition &&
        hs_state->_has_vanished) {
        hs_state->_time = hs_state->_last_known_time;
        hs_state->_until = hs_state->_last_known_time;
        if (!only_update) {
            process(query, hs_state);
        }

        hs_state->_may_no_longer_exist = false;
        hs_state->_has_vanished = false;
        // Set absent state
        hs_state->_state = -1;
        hs_state->_debug_info = "UNMONITORED";
        hs_state->_in_downtime = 0;
        hs_state->_in_notification_period = 0;
        hs_state->_in_service_period = 0;
        hs_state->_is_flapping = 0;
        hs_state->_log_output = "";

        // Apply latest notification period information and set the host_state
        // to unmonitored
        auto it_status =
            _notification_periods.find(hs_state->_notification_period);
        if (it_status != _notification_periods.end()) {
            hs_state->_in_notification_period = it_status->second;
        } else {
            // No notification period information available -> within
            // notification period
            hs_state->_in_notification_period = 1;
        }

        // Same for service period
        it_status = _notification_periods.find(hs_state->_service_period);
        if (it_status != _notification_periods.end()) {
            hs_state->_in_service_period = it_status->second;
        } else {
            // No service period information available -> within service period
            hs_state->_in_service_period = 1;
        }
    }

    // Update basic information
    hs_state->_time = entry->_time;
    hs_state->_lineno = entry->_lineno;
    hs_state->_until = entry->_time;

    // A timeperiod entry never brings an absent host or service into
    // existence..
    if (entry->_type != LogEntryType::timeperiod_transition) {
        hs_state->_may_no_longer_exist = false;
    }

    switch (entry->_type) {
        case LogEntryType::none:
        case LogEntryType::core_starting:
        case LogEntryType::core_stopping:
        case LogEntryType::log_version:
        case LogEntryType::log_initial_states:
        case LogEntryType::acknowledge_alert_host:
        case LogEntryType::acknowledge_alert_service:
            break;
        case LogEntryType::state_host:
        case LogEntryType::state_host_initial:
        case LogEntryType::alert_host: {
            if (hs_state->_is_host) {
                if (hs_state->_state != entry->_state) {
                    if (!only_update) {
                        process(query, hs_state);
                    }
                    hs_state->_state = entry->_state;
                    hs_state->_host_down = static_cast<int>(entry->_state > 0);
                    hs_state->_debug_info = "HOST STATE";
                } else {
                    state_changed = 0;
                }
            } else if (hs_state->_host_down !=
                       static_cast<int>(entry->_state > 0)) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_host_down = static_cast<int>(entry->_state > 0);
                hs_state->_debug_info = "SVC HOST STATE";
            }
            break;
        }
        case LogEntryType::state_service:
        case LogEntryType::state_service_initial:
        case LogEntryType::alert_service: {
            if (hs_state->_state != entry->_state) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "SVC ALERT";
                hs_state->_state = entry->_state;
            }
            break;
        }
        case LogEntryType::downtime_alert_host: {
            int downtime_active =
                starts_with(entry->_state_type, "STARTED") ? 1 : 0;

            if (hs_state->_in_host_downtime != downtime_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info =
                    hs_state->_is_host ? "HOST DOWNTIME" : "SVC HOST DOWNTIME";
                hs_state->_in_host_downtime = downtime_active;
                if (hs_state->_is_host) {
                    hs_state->_in_downtime = downtime_active;
                }
            } else {
                state_changed = 0;
            }
            break;
        }
        case LogEntryType::downtime_alert_service: {
            int downtime_active =
                starts_with(entry->_state_type, "STARTED") ? 1 : 0;
            if (hs_state->_in_downtime != downtime_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "DOWNTIME SERVICE";
                hs_state->_in_downtime = downtime_active;
            }
            break;
        }
        case LogEntryType::flapping_host:
        case LogEntryType::flapping_service: {
            int flapping_active =
                starts_with(entry->_state_type, "STARTED") ? 1 : 0;
            if (hs_state->_is_flapping != flapping_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "FLAPPING ";
                hs_state->_is_flapping = flapping_active;
            } else {
                state_changed = 0;
            }
            break;
        }
        case LogEntryType::timeperiod_transition: {
            try {
                TimeperiodTransition tpt(entry->_options);
                // if no _host pointer is available the initial status of
                // _in_notification_period (1) never changes
                if (hs_state->_host != nullptr &&
                    tpt.name() == hs_state->_notification_period) {
                    if (tpt.to() != hs_state->_in_notification_period) {
                        if (!only_update) {
                            process(query, hs_state);
                        }
                        hs_state->_debug_info = "TIMEPERIOD ";
                        hs_state->_in_notification_period = tpt.to();
                    }
                }
                // same for service period
                if (hs_state->_host != nullptr &&
                    tpt.name() == hs_state->_service_period) {
                    if (tpt.to() != hs_state->_in_service_period) {
                        if (!only_update) {
                            process(query, hs_state);
                        }
                        hs_state->_debug_info = "TIMEPERIOD ";
                        hs_state->_in_service_period = tpt.to();
                    }
                }
            } catch (const std::logic_error &e) {
                Warning(logger())
                    << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                    << entry->_complete;
            }
            break;
        }
    }

    if (entry->_type != LogEntryType::timeperiod_transition) {
        if ((entry->_type == LogEntryType::state_host_initial ||
             entry->_type == LogEntryType::state_service_initial) &&
            entry->_check_output == "(null)") {
            hs_state->_log_output = "";
        } else {
            hs_state->_log_output = entry->_check_output;
        }
    }

    return state_changed;
}

void TableStateHistory::process(Query *query, HostServiceState *hs_state) {
    hs_state->_duration = hs_state->_until - hs_state->_from;
    hs_state->_duration_part = static_cast<double>(hs_state->_duration) /
                               static_cast<double>(_query_timeframe);

    hs_state->_duration_state_UNMONITORED = 0;
    hs_state->_duration_part_UNMONITORED = 0;

    hs_state->_duration_state_OK = 0;
    hs_state->_duration_part_OK = 0;

    hs_state->_duration_state_WARNING = 0;
    hs_state->_duration_part_WARNING = 0;

    hs_state->_duration_state_CRITICAL = 0;
    hs_state->_duration_part_CRITICAL = 0;

    hs_state->_duration_state_UNKNOWN = 0;
    hs_state->_duration_part_UNKNOWN = 0;

    switch (hs_state->_state) {
        case -1:
            hs_state->_duration_state_UNMONITORED = hs_state->_duration;
            hs_state->_duration_part_UNMONITORED = hs_state->_duration_part;
            break;
        case STATE_OK:
            hs_state->_duration_state_OK = hs_state->_duration;
            hs_state->_duration_part_OK = hs_state->_duration_part;
            break;
        case STATE_WARNING:
            hs_state->_duration_state_WARNING = hs_state->_duration;
            hs_state->_duration_part_WARNING = hs_state->_duration_part;
            break;
        case STATE_CRITICAL:
            hs_state->_duration_state_CRITICAL = hs_state->_duration;
            hs_state->_duration_part_CRITICAL = hs_state->_duration_part;
            break;
        case STATE_UNKNOWN:
            hs_state->_duration_state_UNKNOWN = hs_state->_duration;
            hs_state->_duration_part_UNKNOWN = hs_state->_duration_part;
            break;
        default:
            break;
    }

    // if (hs_state->_duration > 0)
    _abort_query = !query->processDataset(Row(hs_state));

    hs_state->_from = hs_state->_until;
}

bool TableStateHistory::isAuthorized(Row row, contact *ctc) {
    auto entry = rowData<HostServiceState>(row);
    service *svc = entry->_service;
    host *hst = entry->_host;
    return (hst != nullptr || svc != nullptr) &&
           is_authorized_for(core(), ctc, hst, svc);
}

shared_ptr<Column> TableStateHistory::column(string colname) {
    // First try to find column in the usual way
    if (auto col = Table::column(colname)) {
        return col;
    }

    // Now try with prefix "current_", since our joined
    // tables have this prefix in order to make clear that
    // we access current and not historic data and in order
    // to prevent mixing up historic and current fields with
    // the same name.
    return Table::column(string("current_") + colname);
}
