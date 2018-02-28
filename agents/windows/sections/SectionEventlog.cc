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
#include <fstream>
#include "Environment.h"
#include "Logger.h"
#include "WinApiAdaptor.h"
#include "stringutil.h"

namespace {

using uint64limits = std::numeric_limits<uint64_t>;

std::pair<char, EventlogLevel> getEventState(const IEventLogRecord &event,
                                             EventlogLevel level) {
    switch (event.level()) {
        case IEventLogRecord::Level::Error:
            return {'C', EventlogLevel::Crit};
        case IEventLogRecord::Level::Warning:
            return {'W', EventlogLevel::Warn};
        case IEventLogRecord::Level::Information:
        case IEventLogRecord::Level::AuditSuccess:
        case IEventLogRecord::Level::Success:
            if (level == EventlogLevel::All)
                return {'O', level};
            else
                return {'.', level};
        case IEventLogRecord::Level::AuditFailure:
            return {'C', EventlogLevel::Crit};
        default:
            return {'u', EventlogLevel::Warn};
    }
}

inline bool isToBeOutput(char type_char, bool hide_context) {
    if (!hide_context) {
        return true;
    }

    return type_char != '.';
}

std::ostream &operator<<(std::ostream &out, const IEventLogRecord &event) {
    // convert UNIX timestamp to local time
    time_t time_generated = static_cast<time_t>(event.timeGenerated());
    struct tm *t = localtime(&time_generated);
    char timestamp[64];
    strftime(timestamp, sizeof(timestamp), "%b %d %H:%M:%S", t);

    // source is the application that produced the event
    std::string source_name = to_utf8(event.source());
    std::replace(source_name.begin(), source_name.end(), ' ', '_');

    return out << timestamp << " " << event.eventQualifiers() << "."
               << event.eventId() << " " << source_name << " "
               << Utf8(event.message()) << "\n";
}

std::pair<uint64_t, EventlogLevel> processEventLog(
    IEventLog &log, uint64_t previouslyReadId, EventlogLevel level,
    const std::function<EventlogLevel(const IEventLogRecord &, EventlogLevel)>
        &processFunc) {
    // we must seek past the previously read event - if there was one
    const uint64_t seekPosition =
        previouslyReadId + (uint64limits::max() == previouslyReadId ? 0 : 1);
    EventlogLevel worstState{EventlogLevel::All};
    uint64_t lastRecordId = previouslyReadId;
    // WARNING:
    // seek implementations for pre-Vista and post-Vista are completely
    // different.
    // seek *must not* return any value as it is different between pre/post
    // Vista.
    log.seek(seekPosition);
    while (auto record = std::move(log.read())) {
        lastRecordId = record->recordId();
        worstState = std::max(worstState, processFunc(*record, level));
    }

    return {lastRecordId, worstState};
}

inline std::ostream &operator<<(std::ostream &out,
                                const eventlog_file_state &state) {
    return out << state.name << "|" << state.record_no;
}

inline bool handleMissingLog(std::ostream &out,
                             const eventlog_file_state &state) {
    bool missing = !state.newly_discovered;
    if (missing) {
        out << "[[[" << state.name << ":missing]]]\n";
    }
    return missing;
}

inline bool hasPreviousState(eventlog_file_state &state) {
    return uint64limits::max() != state.record_no;
}

eventlog_hints_t loadEventlogOffsets(const std::string &statefile,
                                     Logger *logger) {
    eventlog_hints_t hints;
    std::ifstream ifs(statefile);
    std::string line;
    while (std::getline(ifs, line)) {
        try {
            hints.push_back(parseStateLine(line));
        } catch (const StateParseError &e) {
            Error(logger) << e.what();
        }
    }

    return hints;
}

}  // namespace

eventlog_hint_t parseStateLine(const std::string &line) {
    /* Example: line = "System|1234" */
    const auto tokens = tokenize(line, "\\|");

    if (tokens.size() != 2 ||
        std::any_of(tokens.cbegin(), tokens.cend(),
                    [](const std::string &t) { return t.empty(); })) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }

    try {
        return {tokens[0], std::stoull(tokens[1])};
    } catch (const std::invalid_argument &) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }
}

template <>
eventlog_config_entry from_string<eventlog_config_entry>(
    const WinApiAdaptor &, const std::string &value) {
    // this parses only what's on the right side of the = in the configuration
    // file
    std::stringstream str(value);

    bool hide_context = false;
    EventlogLevel level{EventlogLevel::All};

    std::string entry;
    while (std::getline(str, entry, ' ')) {
        if (entry == "nocontext")
            hide_context = true;
        else if (entry == "off")
            level = EventlogLevel::Off;
        else if (entry == "all")
            level = EventlogLevel::All;
        else if (entry == "warn")
            level = EventlogLevel::Warn;
        else if (entry == "crit")
            level = EventlogLevel::Crit;
        else {
            std::cerr << "Invalid log level '" << entry << "'." << std::endl
                      << "Allowed are off, all, warn and crit." << std::endl;
        }
    }

    return eventlog_config_entry("", level, hide_context, false);
}

std::ostream &operator<<(std::ostream &out, const eventlog_config_entry &val) {
    out << val.name << " = ";
    if (val.hide_context) {
        out << "nocontext ";
    }
    out << val.level;
    return out;
}

SectionEventlog::SectionEventlog(Configuration &config, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("logwatch", "logwatch", config.getEnvironment(), logger, winapi)
    , _send_initial(config, "logwatch", "sendall", false, winapi)
    , _vista_api(config, "logwatch", "vista_api", false, winapi)
    , _config(config, "logwatch", "logname", winapi)
    , _hints(loadEventlogOffsets(_env.eventlogStatefile(), logger)) {
    // register a second key-name
    config.reg("logwatch", "logfile", &_config);
}

SectionEventlog::~SectionEventlog() {}

void SectionEventlog::saveEventlogOffsets(const std::string &statefile) {
    std::ofstream ofs(statefile);

    if (!ofs) {
        std::cerr << "failed to open " << statefile << " for writing"
                  << std::endl;
        return;
    }

    for (const auto &state : _state) {
        EventlogLevel level{EventlogLevel::Warn};
        std::tie(level, std::ignore) = readConfig(state);
        if (level != EventlogLevel::Off) {
            ofs << state << std::endl;
        }
    }
}

uint64_t SectionEventlog::outputEventlog(std::ostream &out, IEventLog &log,
                                         uint64_t previouslyReadId,
                                         EventlogLevel level,
                                         bool hideContext) {
    const auto getState = [](const IEventLogRecord &record,
                             EventlogLevel level) {
        return getEventState(record, level).second;
    };
    uint64_t lastReadId = 0;
    EventlogLevel worstState{EventlogLevel::All};

    // first pass - determine if there are records above level
    std::tie(lastReadId, worstState) =
        processEventLog(log, previouslyReadId, level, getState);
    Debug(_logger) << "    . worst state: " << static_cast<int>(worstState);

    // second pass - if there were, print everything
    if (worstState >= level) {
        const auto outputRecord = [&out, hideContext](
            const IEventLogRecord &record, EventlogLevel level) {
            char type_char{'\0'};
            EventlogLevel dummy{EventlogLevel::Off};
            std::tie(type_char, dummy) = getEventState(record, level);
            if (isToBeOutput(type_char, hideContext)) {
                out << type_char << " " << record;
            }
            return dummy;  // Dummy return value, ignored by caller
        };
        std::tie(lastReadId, std::ignore) =
            processEventLog(log, previouslyReadId, level, outputRecord);
    }

    return lastReadId;
}

// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void SectionEventlog::registerEventlog(const char *logname) {
    // check if we already know this one...
    for (auto &state : _state) {
        if (ci_equal(state.name, logname)) {
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
    for (auto &state : _state) {
        state.newly_discovered = false;
    }

    char regpath[128];
    snprintf(regpath, sizeof(regpath),
             "SYSTEM\\CurrentControlSet\\Services\\Eventlog");
    HKEY key = nullptr;
    DWORD ret = _winapi.RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath, 0,
                                     KEY_ENUMERATE_SUB_KEYS, &key);
    HKeyHandle hKey{key, _winapi};
    bool success = true;
    if (ret == ERROR_SUCCESS) {
        DWORD i = 0;
        char buffer[128];
        DWORD len;
        while (true) {
            len = sizeof(buffer);
            DWORD r = _winapi.RegEnumKeyEx(hKey.get(), i, buffer, &len, NULL,
                                           NULL, NULL, NULL);
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

void SectionEventlog::readHintOffsets() {
    // Special handling on startup (first_run)
    // The last processed record number of each eventlog is stored in the
    // file eventstate.txt
    if (_first_run && !*_send_initial) {
        for (auto &state : _state) {
            auto it = std::find_if(
                _hints.cbegin(), _hints.cend(),
                [&state](const auto &hint) { return state.name == hint.name; });
            // If there is no entry for the given eventlog we start at the
            // end
            state.record_no =
                it != _hints.cend() ? it->record_no : uint64limits::max();
        }
    }
}

std::pair<EventlogLevel, bool> SectionEventlog::readConfig(
    const eventlog_file_state &state) const {
    // Get the configuration of that log file (which messages to
    // send)
    auto it = std::find_if(
        _config->cbegin(), _config->cend(), [&state](const auto &config) {
            return config.name == "*" || ci_equal(config.name, state.name);
        });
    return it != _config->cend()
               ? std::make_pair(it->level, it->hide_context != 0)
               : std::make_pair(EventlogLevel::Warn, false);
}

std::unique_ptr<IEventLog> SectionEventlog::openEventlog(
    const std::string &logname, std::ostream &out) const {
    Debug(_logger) << " - event log \"" << logname << "\":";

    try {
        std::unique_ptr<IEventLog> log(open_eventlog(
            to_utf16(logname.c_str(), _winapi), *_vista_api, _logger, _winapi));

        Debug(_logger) << "   . successfully opened event log";
        out << "[[[" << logname << "]]]\n";
        return log;
    } catch (const std::exception &e) {
        Error(_logger) << "failed to read event log: " << e.what() << std::endl;
        out << "[[[" << logname << ":missing]]]\n";
        return nullptr;
    }
}

void SectionEventlog::handleExistingLog(std::ostream &out,
                                        eventlog_file_state &state) {
    EventlogLevel level{EventlogLevel::Warn};
    bool hideContext = false;
    std::tie(level, hideContext) = readConfig(state);

    if (level == EventlogLevel::Off) return;

    if (const auto log = openEventlog(state.name, out)) {
        if (hasPreviousState(state)) {
            // The last processed eventlog record will serve as previous state
            // (= saved offset) for the next call.
            state.record_no =
                outputEventlog(out, *log, state.record_no, level, hideContext);
        } else {
            // We just started monitoring this log. There was no previous state
            // saved. Just save the last record, it will serve as saved previous
            // state (= offset) for the next call.
            state.record_no = log->getLastRecordId();
        }
    }
}

// The output of this section is compatible with
// the logwatch agent for Linux and UNIX
bool SectionEventlog::produceOutputInner(std::ostream &out) {
    Debug(_logger) << "SectionEventlog::produceOutputInner";
    // This agent remembers the record numbers
    // of the event logs up to which messages have
    // been processed. When started, the eventlog
    // is skipped to the end. Historic messages are
    // not been processed.

    if (find_eventlogs(out)) {
        readHintOffsets();

        for (auto &state : _state) {
            if (!handleMissingLog(out, state)) {
                handleExistingLog(out, state);
            }
        }
        // The offsets are persisted in file after each run as we never know
        // when the agent will be stopped.
        saveEventlogOffsets(_env.eventlogStatefile());
    }
    _first_run = false;
    return true;
}
