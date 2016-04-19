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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableStateHistory.h"
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <time.h>
#include <deque>
#include <set>
#include <utility>
#include "Column.h"
#include "Filter.h"
#include "HostServiceState.h"
#include "LogEntry.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeColumn.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "logger.h"
#include "mk/Mutex.h"

#ifdef CMC
#include "Host.h"
#include "Service.h"
#include "Timeperiod.h"
#define STATE_OK 0
#define STATE_WARNING 1
#define STATE_CRITICAL 2
#define STATE_UNKNOWN 3
#else
#include "auth.h"
#endif

using mk::lock_guard;
using mk::mutex;
using std::deque;
using std::make_pair;
using std::map;
using std::set;
using std::string;

int g_disable_statehist_filtering = 0;

#ifndef CMC
const char *getCustomVariable(customvariablesmember *cvm, const char *name) {
    while (cvm != nullptr) {
        if (strcmp(cvm->variable_name, name) == 0) {
            return cvm->variable_value;
        }
        cvm = cvm->next;
    }
    return "";
}
#endif

TableStateHistory::TableStateHistory(LogCache *log_cache)
    : _log_cache(log_cache) {
    addColumns(this);
}

// static
void TableStateHistory::addColumns(Table *table) {
    HostServiceState *ref = nullptr;
    table->addColumn(new OffsetTimeColumn(
        "time", "Time of the log event (seconds since 1/1/1970)",
        reinterpret_cast<char *>(&(ref->_time)) - reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(
        new OffsetIntColumn("lineno", "The number of the line in the log file",
                            reinterpret_cast<char *>(&(ref->_lineno)) -
                                reinterpret_cast<char *>(ref),
                            -1));
    table->addColumn(new OffsetTimeColumn(
        "from", "Start time of state (seconds since 1/1/1970)",
        reinterpret_cast<char *>(&(ref->_from)) - reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetTimeColumn(
        "until", "End time of state (seconds since 1/1/1970)",
        reinterpret_cast<char *>(&(ref->_until)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(
        new OffsetIntColumn("duration", "Duration of state (until - from)",
                            reinterpret_cast<char *>(&(ref->_duration)) -
                                reinterpret_cast<char *>(ref),
                            -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part", "Duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "state",
        "The state of the host or service in question - OK(0) / WARNING(1) / "
        "CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)",
        reinterpret_cast<char *>(&(ref->_state)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "host_down", "Shows if the host of this service is down",
        reinterpret_cast<char *>(&(ref->_host_down)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "in_downtime", "Shows if the host or service is in downtime",
        reinterpret_cast<char *>(&(ref->_in_downtime)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "in_host_downtime", "Shows if the host of this service is in downtime",
        reinterpret_cast<char *>(&(ref->_in_host_downtime)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "is_flapping", "Shows if the host or service is flapping",
        reinterpret_cast<char *>(&(ref->_is_flapping)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "in_notification_period",
        "Shows if the host or service is within its notification period",
        reinterpret_cast<char *>(&(ref->_in_notification_period)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetStringColumn(
        "notification_period",
        "The notification period of the host or service in question",
        reinterpret_cast<char *>(&(ref->_notification_period)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "in_service_period",
        "Shows if the host or service is within its service period",
        reinterpret_cast<char *>(&(ref->_in_service_period)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetStringColumn(
        "service_period",
        "The service period of the host or service in question",
        reinterpret_cast<char *>(&(ref->_service_period)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(
        new OffsetStringColumn("debug_info", "Debug information",
                               reinterpret_cast<char *>(&(ref->_debug_info)) -
                                   reinterpret_cast<char *>(ref),
                               -1));
    table->addColumn(new OffsetStringColumn(
        "host_name", "Host name", reinterpret_cast<char *>(&(ref->_host_name)) -
                                      reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetStringColumn(
        "service_description", "Description of the service",
        reinterpret_cast<char *>(&(ref->_service_description)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetStringColumn(
        "log_output", "Logfile output relevant for this state",
        reinterpret_cast<char *>(&(ref->_log_output)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetIntColumn(
        "duration_ok", "OK duration of state ( until - from )",
        reinterpret_cast<char *>(&(ref->_duration_state_OK)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part_ok", "OK duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part_OK) -
            reinterpret_cast<char *>(ref),
        -1));

    table->addColumn(new OffsetIntColumn(
        "duration_warning", "WARNING duration of state (until - from)",
        reinterpret_cast<char *>(&(ref->_duration_state_WARNING)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part_warning",
        "WARNING duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part_WARNING) -
            reinterpret_cast<char *>(ref),
        -1));

    table->addColumn(new OffsetIntColumn(
        "duration_critical", "CRITICAL duration of state (until - from)",
        reinterpret_cast<char *>(&(ref->_duration_state_CRITICAL)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part_critical",
        "CRITICAL duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part_CRITICAL) -
            reinterpret_cast<char *>(ref),
        -1));

    table->addColumn(new OffsetIntColumn(
        "duration_unknown", "UNKNOWN duration of state (until - from)",
        reinterpret_cast<char *>(&(ref->_duration_state_UNKNOWN)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part_unknown",
        "UNKNOWN duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part_UNKNOWN) -
            reinterpret_cast<char *>(ref),
        -1));

    table->addColumn(new OffsetIntColumn(
        "duration_unmonitored", "UNMONITORED duration of state (until - from)",
        reinterpret_cast<char *>(&(ref->_duration_state_UNMONITORED)) -
            reinterpret_cast<char *>(ref),
        -1));
    table->addColumn(new OffsetDoubleColumn(
        "duration_part_unmonitored",
        "UNMONITORED duration part in regard to the query timeframe",
        reinterpret_cast<char *>(&ref->_duration_part_UNMONITORED) -
            reinterpret_cast<char *>(ref),
        -1));

    // join host and service tables
    TableHosts::addColumns(table, "current_host_",
                           reinterpret_cast<char *>(&(ref->_host)) -
                               reinterpret_cast<char *>(ref));
    TableServices::addColumns(table, "current_service_",
                              reinterpret_cast<char *>(&(ref->_service)) -
                                  reinterpret_cast<char *>(ref),
                              false /* no hosts table */);
}

LogEntry *TableStateHistory::getPreviousLogentry() {
    while (_it_entries == _entries->begin()) {
        // open previous logfile
        if (_it_logs == _log_cache->logfiles()->begin()) {
            return nullptr;
        }
        --_it_logs;
        _entries = _it_logs->second->getEntriesFromQuery(
            _query, _log_cache, _since, _until, CLASSMASK_STATEHIST);
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
            _query, _log_cache, _since, _until, CLASSMASK_STATEHIST);
        _it_entries = _entries->begin();
    }
    return _it_entries->second;
}

void TableStateHistory::answerQuery(Query *query) {
    // Create a partial filter, that contains only such filters that
    // check attributes of current hosts and services
    typedef deque<Filter *> object_filter_t;
    object_filter_t object_filter;

    if (g_disable_statehist_filtering == 0) {
        for (auto filter : *query->filter()) {
            Column *column = filter->column();
            if (column != nullptr) {
                const char *column_name = column->name();
                if ((strncmp(column_name, "current_", 8) == 0) ||
                    (strncmp(column_name, "host_", 5) == 0) ||
                    (strncmp(column_name, "service_", 8) == 0)) {
                    object_filter.push_back(filter);
                    // logger(LOG_NOTICE, "Nehme Column: %s", column_name);
                } else {
                    // logger(LOG_NOTICE, "Column geht nciht: %s", column_name);
                }
            } else {
                // logger(LOG_NOTICE, "Mist: Filter ohne Column");
            }
        }
    }

    lock_guard<mutex> lg(_log_cache->_lock);
    _log_cache->logCachePreChecks();

    // This flag might be set to true by the return value of processDataset(...)
    _abort_query = false;

    // Keep track of the historic state of services/hosts here
    typedef map<HostServiceKey, HostServiceState *> state_info_t;
    state_info_t state_info;

    // Store hosts/services that we have filtered out here
    typedef set<HostServiceKey> object_blacklist_t;
    object_blacklist_t object_blacklist;

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
        query->setError(
            RESPONSE_CODE_INVALID_REQUEST,
            "Start of timeframe required. e.g. Filter: time > 1234567890");
        return;
    }

    _query_timeframe = _until - _since - 1;
    if (_query_timeframe == 0) {
        query->setError(RESPONSE_CODE_INVALID_REQUEST,
                        "Query timeframe is 0 seconds");
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
        query, _log_cache, _since, _until, CLASSMASK_STATEHIST);
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
            !(entry->_type == STATE_SERVICE_INITIAL ||
              entry->_type == STATE_HOST_INITIAL)) {
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
            case NONE:
            case CORE_STARTING:
            case CORE_STOPPING:
            case LOG_VERSION:
            case ACKNOWLEDGE_ALERT_HOST:
            case ACKNOWLEDGE_ALERT_SERVICE:
                break;
            case ALERT_SERVICE:
            case STATE_SERVICE:
            case STATE_SERVICE_INITIAL:
            case DOWNTIME_ALERT_SERVICE:
            case FLAPPING_SERVICE:
                key = entry->_service;
                is_service = true;
            // fall-through
            case ALERT_HOST:
            case STATE_HOST:
            case STATE_HOST_INITIAL:
            case DOWNTIME_ALERT_HOST:
            case FLAPPING_HOST: {
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
                    state->_is_host = entry->_svc_desc == nullptr;
                    state->_host = entry->_host;
                    state->_service = entry->_service;
#ifdef CMC
                    state->_host_name = entry->_host->_name;
                    state->_service_description = entry->_service != nullptr
                                                      ? entry->_service->_name
                                                      : "";
#else
                    state->_host_name = entry->_host->name;
                    state->_service_description =
                        entry->_service != nullptr
                            ? entry->_service->description
                            : "";
#endif

                    // No state found. Now check if this host/services is
                    // filtered out.
                    // Note: we currently do not filter out hosts since they
                    // might be
                    // needed for service states
                    if (entry->_svc_desc != nullptr) {
                        bool filtered_out = false;
                        for (auto filter : object_filter) {
                            if (!filter->accepts(state)) {
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
                    state_info.insert(make_pair(key, state));
                    state->_from = _since;

                    // Get notification period of host/service
                    // If this host/service is no longer availabe in nagios ->
                    // set to ""
                    if (state->_service != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_service->notificationPeriod()->name();
#else
                        state->_notification_period =
                            state->_service->notification_period;
#endif
                    } else if (state->_host != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_host->notificationPeriod()->name();
#else
                        state->_notification_period =
                            state->_host->notification_period;
#endif
                    } else {
                        state->_notification_period = "";

                        // If for some reason the notification period is missing
                        // set
                        // a default
                    }
                    if (state->_notification_period == nullptr) {
                        state->_notification_period = "";
                    }

                    // Same for service period. For Nagios this is a bit
                    // different, since this
                    // is no native field but just a custom variable
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

                        // Determine initial in_notification_period status
                    }
                    _notification_periods_t::const_iterator tmp_period =
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
                if (entry->_type == ALERT_HOST || entry->_type == STATE_HOST ||
                    entry->_type == DOWNTIME_ALERT_HOST) {
                    if (state_changed != 0) {
                        for (auto &_service : state->_services) {
                            updateHostServiceState(query, entry, _service,
                                                   only_update);
                        }
                    }
                }
                break;
            }
            case TIMEPERIOD_TRANSITION: {
                char *save_ptr;
                char *buffer = strdup(entry->_options);
                char *tp_name = strtok_r(buffer, ";", &save_ptr);
                char *tp_state = strtok_r(nullptr, ";", &save_ptr);
                if (tp_state != nullptr) {
                    tp_state = strtok_r(nullptr, ";", &save_ptr);
                }

                if (tp_state == nullptr) {
                    // This line is broken...
                    logger(LOG_WARNING,
                           "Error: Invalid syntax of TIMEPERIOD TRANSITION: %s",
                           entry->_complete);
                    free(buffer);
                    break;
                }

                _notification_periods[tp_name] = atoi(tp_state);
                for (auto &it_hst : state_info) {
                    updateHostServiceState(query, entry, it_hst.second,
                                           only_update);
                }
                free(buffer);
                break;
            }
            case LOG_INITIAL_STATES: {
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
                if (hst->_log_output != nullptr) {
                    free(hst->_log_output);
                }
                hst->_log_output = nullptr;
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
    if (entry->_type != TIMEPERIOD_TRANSITION && hs_state->_has_vanished) {
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
        if (hs_state->_log_output != nullptr) {
            free(hs_state->_log_output);
        }
        hs_state->_log_output = nullptr;

        // Apply latest notification period information and set the host_state
        // to unmonitored
        _notification_periods_t::const_iterator it_status =
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
    if (entry->_type != TIMEPERIOD_TRANSITION) {
        hs_state->_may_no_longer_exist = false;
    }

    switch (entry->_type) {
        case NONE:
        case CORE_STARTING:
        case CORE_STOPPING:
        case LOG_VERSION:
        case LOG_INITIAL_STATES:
        case ACKNOWLEDGE_ALERT_HOST:
        case ACKNOWLEDGE_ALERT_SERVICE:
            break;
        case STATE_HOST:
        case STATE_HOST_INITIAL:
        case ALERT_HOST: {
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
        case STATE_SERVICE:
        case STATE_SERVICE_INITIAL:
        case ALERT_SERVICE: {
            if (hs_state->_state != entry->_state) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "SVC ALERT";
                hs_state->_state = entry->_state;
            }
            break;
        }
        case DOWNTIME_ALERT_HOST: {
            int downtime_active =
                strncmp(entry->_state_type, "STARTED", 7) == 0 ? 1 : 0;

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
        case DOWNTIME_ALERT_SERVICE: {
            int downtime_active =
                strncmp(entry->_state_type, "STARTED", 7) == 0 ? 1 : 0;
            if (hs_state->_in_downtime != downtime_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "DOWNTIME SERVICE";
                hs_state->_in_downtime = downtime_active;
            }
            break;
        }
        case FLAPPING_HOST:
        case FLAPPING_SERVICE: {
            int flapping_active =
                strncmp(entry->_state_type, "STARTED", 7) == 0 ? 1 : 0;
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
        case TIMEPERIOD_TRANSITION: {
            char *save_ptr;
            char *buffer = strdup(entry->_options);
            char *tp_name = strtok_r(buffer, ";", &save_ptr);
            strtok_r(nullptr, ";", &save_ptr);
            char *tp_state = strtok_r(nullptr, ";", &save_ptr);

            // if no _host pointer is available the initial status of
            // _in_notification_period (1) never changes
            if ((hs_state->_host != nullptr) &&
                (strcmp(tp_name, hs_state->_notification_period) == 0)) {
                int new_status = atoi(tp_state);
                if (new_status != hs_state->_in_notification_period) {
                    if (!only_update) {
                        process(query, hs_state);
                    }
                    hs_state->_debug_info = "TIMEPERIOD ";
                    hs_state->_in_notification_period = new_status;
                }
            }
            // same for service period
            if ((hs_state->_host != nullptr) &&
                (strcmp(tp_name, hs_state->_service_period) == 0)) {
                int new_status = atoi(tp_state);
                if (new_status != hs_state->_in_service_period) {
                    if (!only_update) {
                        process(query, hs_state);
                    }
                    hs_state->_debug_info = "TIMEPERIOD ";
                    hs_state->_in_service_period = new_status;
                }
            }
            free(buffer);
            break;
        }
    }

    if (entry->_type != TIMEPERIOD_TRANSITION) {
        if (hs_state->_log_output != nullptr) {
            free(hs_state->_log_output);
        }

        if ((entry->_type == STATE_HOST_INITIAL ||
             entry->_type == STATE_SERVICE_INITIAL) &&
            (entry->_check_output != nullptr &&
             (strcmp(entry->_check_output, "(null)") == 0))) {
            hs_state->_log_output = nullptr;

        } else {
            // TODO(sp): Do we really need to strdup? How are the lifetimes of
            // entry and hs_state related? This is highly unclear. This strdup
            // complicates things like hell, because HostServiceState owns
            // _log_output because of it. If this is really needed (hopefully
            // not), we should better change the type from a naked pointer to a
            // unique_ptr, but this would mean introducing yet another Column
            // subclass, because the Column framework is not flexible at all
            // regarding the types it handles.
            hs_state->_log_output = entry->_check_output != nullptr
                                        ? strdup(entry->_check_output)
                                        : nullptr;
        }
    }

    return state_changed;
}

void TableStateHistory::process(Query *query, HostServiceState *hs_state) {
    hs_state->_duration = hs_state->_until - hs_state->_from;
    hs_state->_duration_part = static_cast<double>(hs_state->_duration) /
                               static_cast<double>(_query_timeframe);

    bzero(&hs_state->_duration_state_UNMONITORED,
          sizeof(time_t) * 5 + sizeof(double) * 5);

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
    _abort_query = !query->processDataset(hs_state);

    hs_state->_from = hs_state->_until;
}

bool TableStateHistory::isAuthorized(contact *ctc, void *data) {
    HostServiceState *entry = static_cast<HostServiceState *>(data);
    service *svc = entry->_service;
    host *hst = entry->_host;

    if ((hst != nullptr) || (svc != nullptr)) {
        return static_cast<int>(is_authorized_for(ctc, hst, svc)) != 0;
    }
    return false;
}

Column *TableStateHistory::column(const char *colname) {
    // First try to find column in the usual way
    Column *col = Table::column(colname);
    if (col != nullptr) {
        return col;
    }

    // Now try with prefix "current_", since our joined
    // tables have this prefix in order to make clear that
    // we access current and not historic data and in order
    // to prevent mixing up historic and current fields with
    // the same name.
    string with_current = string("current_") + colname;
    return Table::column(with_current.c_str());
}
