// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

#define __STDC_FORMAT_MACROS
#include "SectionEventlog.h"
#include <inttypes.h>
#include <cstring>
#include <ctime>
#include "../Environment.h"
#include "../Logger.h"
#include "../WinApiAdaptor.h"
#include "../stringutil.h"

SectionEventlog::SectionEventlog(Configuration &config, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("logwatch", config.getEnvironment(), logger, winapi)
    , _send_initial(config, "logwatch", "sendall", false, winapi)
    , _vista_api(config, "logwatch", "vista_api", false, winapi)
    , _config(config, "logwatch", "logname", winapi) {
    // register a second key-name
    config.reg("logwatch", "logfile", &_config);
}

SectionEventlog::~SectionEventlog() {
    _state.clear();
    for (auto ptr : _hints) {
        free(ptr->name);
        delete ptr;
    }
    _hints.clear();
}

void SectionEventlog::parseStateLine(char *line) {
    /* Example: line = "System|1234" */
    rstrip(line);
    char *p = line;
    while (*p && *p != '|') p++;
    *p = 0;
    char *path = line;
    p++;

    char *token = strtok(p, "|");

    if (!token) return;

    eventlog_hint_t *elh = new eventlog_hint_t();
    elh->name = strdup(path);
    elh->record_no = std::stoull(token);
    _hints.push_back(elh);
}

void SectionEventlog::loadEventlogOffsets(const std::string &statefile) {
    static bool records_loaded = false;
    if (!records_loaded) {
        FILE *file = fopen(statefile.c_str(), "r");
        if (file) {
            char line[256];
            while (NULL != fgets(line, sizeof(line), file)) {
                parseStateLine(line);
            }
            fclose(file);
        }
        records_loaded = true;
    }
}

void SectionEventlog::saveEventlogOffsets(const std::string &statefile) {
    FILE *file = fopen(statefile.c_str(), "w");
    if (file == nullptr) {
        fprintf(stderr, "failed to open %s for writing\n", statefile.c_str());
        return;
    }
    for (eventlog_file_state &state : _state) {
        int level = 1;
        for (eventlog_config_entry &config : *_config) {
            if ((config.name == "*") || ci_equal(config.name, state.name)) {
                level = config.level;
                break;
            }
        }
        if (level != -1)
            fprintf(file, "%s|%" PRIu64 "\n", state.name.c_str(),
                    state.record_no);
    }
    fclose(file);
}

static std::pair<char, int> determine_event_state(const IEventLogRecord &event,
                                                  int level) {
    switch (event.level()) {
        case IEventLogRecord::Level::Error:
            return {'C', 2};
        case IEventLogRecord::Level::Warning:
            return {'W', 1};
        case IEventLogRecord::Level::Information:
        case IEventLogRecord::Level::AuditSuccess:
        case IEventLogRecord::Level::Success:
            if (level == 0)
                return {'O', 0};
            else
                return {'.', 0};
        case IEventLogRecord::Level::AuditFailure:
            return {'C', 2};
        default:
            return {'u', 1};
    }
}

void SectionEventlog::process_eventlog_entry(std::ostream &out,
                                             const IEventLog &event_log,
                                             const IEventLogRecord &event,
                                             int level, int hide_context) {
    char type_char;
    int this_state;
    std::tie(type_char, this_state) = determine_event_state(event, level);

    if (hide_context && (type_char == '.')) {
        return;
    }

    // convert UNIX timestamp to local time
    time_t time_generated = (time_t)event.timeGenerated();
    struct tm *t = localtime(&time_generated);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);

    // source is the application that produced the event
    std::string source_name = to_utf8(event.source());
    std::replace(source_name.begin(), source_name.end(), ' ', '_');
    auto message = event.message();
    // Nice surprise: EvtFormatMessage (used by Vista API) delivers wstring
    // messages with trailing null character within the allocated wstring size!
    // Later, this causes the socket output to be cut at the 1st null character,
    // so we need to trim trailing null(s) away here.
    while (message.back() == L'\0') {
        message.resize(message.size() - 1);
    }
    out << type_char << " " << timestamp << " " << event.eventQualifiers()
        << "." << event.eventId() << " " << Utf8(event.source()) << " "
        << Utf8(message) << "\n";
}

void SectionEventlog::outputEventlog(std::ostream &out, const char *logname,
                                     uint64_t &first_record, int level,
                                     int hide_context) {
    Debug(_logger) << " - event log \"" << logname << "\":";

    try {
        std::unique_ptr<IEventLog> log(open_eventlog(
            to_utf16(logname, _winapi), *_vista_api, _logger, _winapi));
        {
            Debug(_logger) << "   . successfully opened event log";

            out << "[[[" << logname << "]]]\n";
            int worst_state = 0;
            // record_number is the last event we read, so we want to seek past
            // it
            bool record_maxxed =
                std::numeric_limits<uint64_t>::max() == first_record;
            first_record = log->seek(first_record + (record_maxxed ? 0 : 1));

            uint64_t last_record = first_record;

            // first pass - determine if there are records above level
            std::shared_ptr<IEventLogRecord> record = log->read();

            while (record.get() != nullptr) {
                std::pair<char, int> state =
                    determine_event_state(*record, level);
                worst_state = std::max(worst_state, state.second);

                last_record = record->recordId();
                record = log->read();
            }

            Debug(_logger) << "    . worst state: " << worst_state;

            // second pass - if there were, print everything
            if (worst_state >= level) {
                log->reset();
                bool record_maxxed =
                    std::numeric_limits<uint64_t>::max() == first_record;
                log->seek(first_record + (record_maxxed ? 0 : 1));

                std::shared_ptr<IEventLogRecord> record = log->read();
                while (record.get() != nullptr) {
                    process_eventlog_entry(out, *log, *record, level,
                                           hide_context);

                    // store highest record number we found
                    last_record = record->recordId();
                    record = log->read();
                }
            }
            first_record = last_record;
        }
    } catch (const std::exception &e) {
        Error(_logger) << "failed to read event log: " << e.what() << std::endl;
        out << "[[[" << logname << ":missing]]]\n";
    }
}

// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void SectionEventlog::registerEventlog(const char *logname) {
    // check if we already know this one...
    for (eventlog_file_state &state : _state) {
        if (state.name.compare(logname) == 0) {
            state.newly_discovered = true;
            return;
        }
    }

    // yet unknown. register it.
    _state.push_back(eventlog_file_state(logname));
}

/* Look into the registry in order to find out, which
   event logs are available. */
bool SectionEventlog::find_eventlogs(std::ostream &out) {
    for (eventlog_file_state &state : _state) {
        state.newly_discovered = false;
    }

    char regpath[128];
    snprintf(regpath, sizeof(regpath),
             "SYSTEM\\CurrentControlSet\\Services\\Eventlog");
    HKEY key;
    DWORD ret = _winapi.RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0,
                                     KEY_ENUMERATE_SUB_KEYS, &key);

    bool success = true;
    if (ret == ERROR_SUCCESS) {
        DWORD i = 0;
        char buffer[128];
        DWORD len;
        while (true) {
            len = sizeof(buffer);
            DWORD r = _winapi.RegEnumKeyEx(key, i, buffer, &len, NULL, NULL,
                                           NULL, NULL);
            if (r == ERROR_SUCCESS)
                registerEventlog(buffer);
            else if (r != ERROR_MORE_DATA) {
                if (r != ERROR_NO_MORE_ITEMS) {
                    out << "ERROR: Cannot enumerate over event logs: error "
                           "code "
                        << r << "\n";
                    success = false;
                }
                break;
            }
            i++;
        }
        _winapi.RegCloseKey(key);
    } else {
        success = false;
        const auto lastError = _winapi.GetLastError();
        out << "ERROR: Cannot open registry key " << regpath
            << " for enumeration: error code " << lastError << "\n";
    }

    // enable the vista-style logs if that api is enabled
    if (*_vista_api) {
        for (const auto &eventlog : *_config) {
            if (eventlog.vista_api) {
                registerEventlog(eventlog.name.c_str());
            }
        }
    }

    return success;
}

void SectionEventlog::postprocessConfig() {
    loadEventlogOffsets(_env.eventlogStatefile());
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
bool SectionEventlog::produceOutputInner(std::ostream &out) {
    // This agent remembers the record numbers
    // of the event logs up to which messages have
    // been processed. When started, the eventlog
    // is skipped to the end. Historic messages are
    // not been processed.
    static bool first_run = true;

    if (find_eventlogs(out)) {
        // Special handling on startup (first_run)
        // The last processed record number of each eventlog is stored in the
        // file eventstate.txt
        if (first_run && !*_send_initial) {
            for (eventlog_file_state &state : _state) {
                bool found_hint = false;
                for (eventlog_hint_t *hint : _hints) {
                    if (state.name.compare(hint->name) == 0) {
                        state.record_no = hint->record_no;
                        found_hint = true;
                        break;
                    }
                }
                // If there is no entry for the given eventlog we start at the
                // end
                if (!found_hint) {
                    state.record_no = std::numeric_limits<uint64_t>::max();
                }
            }
        }

        for (eventlog_file_state &state : _state) {
            if (!state.newly_discovered)  // not here any more!
                out << "[[[" << state.name << ":missing]]]\n";
            else {
                // Get the configuration of that log file (which messages to
                // send)
                int level = 1;
                int hide_context = 0;
                for (const eventlog_config_entry &config : *_config) {
                    if ((config.name == "*") ||
                        ci_equal(config.name, state.name)) {
                        level = config.level;
                        hide_context = config.hide_context;
                        break;
                    }
                }
                if (level != -1) {
                    outputEventlog(out, state.name.c_str(), state.record_no,
                                   level, hide_context);
                }
            }
        }
        saveEventlogOffsets(_env.eventlogStatefile());
    }
    first_run = false;
    return true;
}
