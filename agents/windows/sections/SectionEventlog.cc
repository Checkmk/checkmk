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
#include <experimental/filesystem>
#include <fstream>
#include "Environment.h"
#include "Logger.h"
#include "SectionHeader.h"
#include "stringutil.h"

namespace fs = std::experimental::filesystem;

namespace {

using uint64limits = std::numeric_limits<uint64_t>;

std::pair<char, eventlog::Level> getEventState(const EventLogRecordBase &event,
                                               eventlog::Level level) {
    switch (event.level()) {
        case EventLogRecordBase::Level::Error:
            return {'C', eventlog::Level::Crit};
        case EventLogRecordBase::Level::Warning:
            return {'W', eventlog::Level::Warn};
        case EventLogRecordBase::Level::Information:
        case EventLogRecordBase::Level::AuditSuccess:
        case EventLogRecordBase::Level::Success:
            if (level == eventlog::Level::All)
                return {'O', level};
            else
                return {'.', level};
        case EventLogRecordBase::Level::AuditFailure:
            return {'C', eventlog::Level::Crit};
        default:
            return {'u', eventlog::Level::Warn};
    }
}

inline bool isToBeOutput(char type_char, bool hide_context) {
    if (!hide_context) {
        return true;
    }

    return type_char != '.';
}

std::ostream &operator<<(std::ostream &out, const EventLogRecordBase &event) {
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

eventlog::States loadEventlogOffsets(const std::vector<std::string> &statefiles,
                                     bool sendall, Logger *logger) {
    for (const auto &statefile : statefiles) {
        eventlog::States states;
        std::ifstream ifs(statefile);
        std::string line;

        while (std::getline(ifs, line)) {
            try {
                auto state = parseStateLine(line);
                if (sendall) state.record_no = 0;
                states.push_back(state);
            } catch (const StateParseError &e) {
                Error(logger) << e.what();
            }
        }

        std::sort(states.begin(), states.end(),
                  [](const auto &s1, const auto &s2) {
                      return ci_compare(s1.name, s2.name);
                  });

        if (!states.empty()) {
            return states;
        }
    }

    return {};
}

// Keeps memory of an event log we have found. It
// might already be known and will not be stored twice.
void registerEventlog(const std::string &logname, bool sendall,
                      eventlog::States &states) {
    // check if we already know this one...
    for (auto &state : states) {
        if (ci_equal(state.name, logname)) {
            state.newly_discovered = true;
            return;
        }
    }

    // yet unknown. register it.
    states.push_back(
        eventlog::state(logname, sendall ? 0 : uint64limits::max()));
}

bool handleFindResult(const FindResult &result, bool sendall,
                      eventlog::States &states, std::ostream &out) {
    if (const auto & [ r, logname ] = result; r == ERROR_SUCCESS) {
        registerEventlog(logname, sendall, states);
    } else if (r != ERROR_MORE_DATA) {
        if (r != ERROR_NO_MORE_ITEMS) {
            out << "ERROR: Cannot enumerate over event logs: error "
                   "code "
                << r << "\n";
            return false;
        }
    }

    return true;
}

std::pair<uint64_t, eventlog::Level> processEventLog(
    EventLogBase &log, uint64_t previouslyReadId, eventlog::Level level,
    const std::function<eventlog::Level(const EventLogRecordBase &,
                                        eventlog::Level)> &processFunc) {
    // we must seek past the previously read event - if there was one
    const uint64_t seekPosition =
        previouslyReadId + (uint64limits::max() == previouslyReadId ? 0 : 1);
    eventlog::Level worstState{eventlog::Level::All};
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
                                const eventlog::state &state) {
    return out << state.name << "|" << state.record_no;
}

inline bool handleMissingLog(std::ostream &out, const eventlog::state &state) {
    bool missing = !state.newly_discovered;
    if (missing) {
        out << "[[[" << state.name << ":missing]]]\n";
    }
    return missing;
}

inline bool hasPreviousState(eventlog::state &state) {
    return uint64limits::max() != state.record_no;
}

}  // namespace

template <>
eventlog::config from_string<eventlog::config>(const WinApiInterface &,
                                               const std::string &value) {
    // this parses only what's on the right side of the = in the configuration
    // file
    std::stringstream str(value);

    bool hide_context = false;
    eventlog::Level level{eventlog::Level::All};

    std::string entry;
    while (std::getline(str, entry, ' ')) {
        if (entry == "nocontext")
            hide_context = true;
        else if (entry == "off")
            level = eventlog::Level::Off;
        else if (entry == "all")
            level = eventlog::Level::All;
        else if (entry == "warn")
            level = eventlog::Level::Warn;
        else if (entry == "crit")
            level = eventlog::Level::Crit;
        else {
            std::cerr << "Invalid log level '" << entry << "'." << std::endl
                      << "Allowed are off, all, warn and crit." << std::endl;
        }
    }

    return eventlog::config("", level, hide_context);
}

namespace eventlog {

inline std::ostream &operator<<(std::ostream &os, const Level &l) {
    switch (l) {
        case Level::Off:
            return os << "off";
        case Level::All:
            return os << "all";
        case Level::Warn:
            return os << "warn";
        case Level::Crit:
            return os << "crit";
        default:
            return os << "invalid";
    }
}

std::ostream &operator<<(std::ostream &out, const config &val) {
    out << val.name << " = ";
    if (val.hide_context) {
        out << "nocontext ";
    }
    out << val.level;
    return out;
}

void Configurable::feed(const std::string &var, const std::string &value) {
    config entry = from_string<config>(_winapi, value);
    const auto tokens = tokenize(var, " ");

    if (tokens.size() < 2) {
        std::cerr << "Invalid eventlog logname entry: '" << var << "'"
                  << std::endl;
    }

    entry.name = join(std::next(tokens.cbegin()), tokens.cend(), " ");
    add(entry);
}

}  // namespace eventlog

eventlog::state parseStateLine(const std::string &line) {
    /* Example: line = "System|1234" */
    const auto tokens = tokenize(line, "\\|");

    if (tokens.size() != 2 ||
        std::any_of(tokens.cbegin(), tokens.cend(),
                    [](const std::string &t) { return t.empty(); })) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }

    try {
        return {tokens[0], std::stoull(tokens[1]), false};
    } catch (const std::invalid_argument &) {
        throw StateParseError{std::string("Invalid state line: ") + line};
    }
}

std::optional<std::string> getIPSpecificStatefileName(
    const Environment &env, const std::optional<std::string> &remoteIP) {
    if (!remoteIP) return std::nullopt;

    const auto statefile = fs::path(env.eventlogStatefile());
    const auto parentPath = statefile.parent_path();
    const auto stem = statefile.stem();
    const auto extension = statefile.extension();
    auto ipString = remoteIP.value();
    std::transform(ipString.cbegin(), ipString.cend(), ipString.begin(),
                   [](unsigned char c) { return std::isalnum(c) ? c : '_'; });

    return std::make_optional((parentPath / stem).string() + "_" + ipString +
                              extension.string());
}

SectionEventlog::SectionEventlog(Configuration &config, Logger *logger,
                                 const WinApiInterface &winapi)
    : Section("logwatch", config.getEnvironment(), logger, winapi,
              std::make_unique<DefaultHeader>("logwatch", logger))
    , _sendall(config, "logwatch", "sendall", false, winapi)
    , _vista_api(config, "logwatch", "vista_api", false, winapi)
    , _config(config, "logwatch", "logname", winapi) {
    // register a second key-name
    config.reg("logwatch", "logfile", &_config);
}

void SectionEventlog::saveEventlogOffsets(const std::string &statefile,
                                          const eventlog::States &states) {
    std::ofstream ofs(statefile);

    if (!ofs) {
        std::cerr << "failed to open " << statefile << " for writing"
                  << std::endl;
        return;
    }

    for (const auto &state : states) {
        // TODO: use structured binding once [[maybe_unused]] supported by gcc
        auto level{eventlog::Level::Off};
        std::tie(level, std::ignore) = readConfig(state);
        if (level != eventlog::Level::Off) {
            ofs << state << std::endl;
        }
    }
}

uint64_t SectionEventlog::outputEventlog(std::ostream &out, EventLogBase &log,
                                         uint64_t previouslyReadId,
                                         eventlog::Level level,
                                         bool hideContext) {
    const auto getState = [](const EventLogRecordBase &record,
                             eventlog::Level level) {
        return getEventState(record, level).second;
    };

    // first pass - determine if there are records above level
    // clang-format off
    auto [lastReadId, worstState] =
        processEventLog(log, previouslyReadId, level, getState);
    // clang-format on
    Debug(_logger) << "    . worst state: " << static_cast<int>(worstState);

    // second pass - if there were, print everything
    if (worstState >= level) {
        const auto outputRecord = [&out, hideContext](
                                      const EventLogRecordBase &record,
                                      eventlog::Level level) {
            // clang-format off
            const auto [type_char, dummy] = getEventState(record, level);
            // clang-format on
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

FindResult SectionEventlog::findLog(const HKeyHandle &hKey, DWORD index) const {
    std::array<char, 128> buffer{};
    DWORD len = static_cast<DWORD>(buffer.size());
    return {_winapi.RegEnumKeyEx(hKey.get(), index, buffer.data(), &len,
                                 nullptr, nullptr, nullptr, nullptr),
            buffer.data()};
}

void SectionEventlog::registerAdditionalEventlogs(eventlog::States &states) {
    // if vista API enabled, register additional configured logs not in registry
    if (*_vista_api) {
        for (const auto &eventlog : *_config) {
            registerEventlog(eventlog.name, *_sendall, states);
        }
    }
}

/* Look into the registry in order to find out, which
   event logs are available. */
bool SectionEventlog::find_eventlogs(std::ostream &out,
                                     eventlog::States &states) {
    // 1) Find and register ordinary event logs found in registry.
    const std::string regpath{"SYSTEM\\CurrentControlSet\\Services\\Eventlog"};
    HKEY key = nullptr;
    bool success = true;

    if (DWORD r = _winapi.RegOpenKeyEx(HKEY_LOCAL_MACHINE, regpath.c_str(), 0,
                                       KEY_ENUMERATE_SUB_KEYS, &key);
        r == ERROR_SUCCESS) {
        HKeyHandle hKey{key, _winapi};
        for (DWORD i = 0; r == ERROR_SUCCESS || r == ERROR_MORE_DATA; ++i) {
            const auto result = findLog(hKey, i);
            r = result.first;
            success =
                handleFindResult(result, *_sendall, states, out) && success;
        }
    } else {
        success = false;
        const auto lastError = _winapi.GetLastError();
        out << "ERROR: Cannot open registry key " << regpath
            << " for enumeration: error code " << lastError << "\n";
    }
    // 2) Register additional, configured logs that are not in registry.
    //    Note: only supported with vista API enabled.
    registerAdditionalEventlogs(states);
    return success;
}

std::pair<eventlog::Level, bool> SectionEventlog::readConfig(
    const eventlog::state &state) const {
    // Get the configuration of that log file (which messages to
    // send)
    auto it = std::find_if(
        _config->cbegin(), _config->cend(), [&state](const auto &config) {
            return config.name == "*" || ci_equal(config.name, state.name);
        });
    return it != _config->cend()
               ? std::make_pair(it->level, it->hide_context != 0)
               : std::make_pair(eventlog::Level::Warn, false);
}

std::unique_ptr<EventLogBase> SectionEventlog::openEventlog(
    const std::string &logname, std::ostream &out) const {
    Debug(_logger) << " - event log \"" << logname << "\":";

    try {
        std::unique_ptr<EventLogBase> log(
            open_eventlog(to_utf16(logname), *_vista_api, _logger, _winapi));

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
                                        eventlog::state &state) {
    // clang-format off
    const auto [level, hideContext] = readConfig(state);
    // clang-format on

    if (level == eventlog::Level::Off) return;

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
bool SectionEventlog::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &remoteIP) {
    Debug(_logger) << "SectionEventlog::produceOutputInner";
    // The agent reads from a state file the record numbers
    // of the event logs up to which messages have
    // been processed. When no state information is available,
    // the eventlog is skipped to the end (unless the sendall config
    // option is used). Historic messages are not been processed.

    std::vector<std::string> statefiles;

    if (const auto ipSpecificName = getIPSpecificStatefileName(_env, remoteIP);
        ipSpecificName) {
        statefiles.push_back(ipSpecificName.value());
    }

    statefiles.push_back(_env.eventlogStatefile());

    if (auto states = loadEventlogOffsets(statefiles, *_sendall, _logger);
        find_eventlogs(out, states)) {
        for (auto &state : states) {
            if (!handleMissingLog(out, state)) {
                handleExistingLog(out, state);
            }
        }
        // The offsets are persisted in a statefile.
        // Always use the first available statefile name. In case of a TCP/IP
        // connection, this is the host-IP-specific statefile, and in case of
        // non-TCP (test / debug run etc.) the general eventstate.txt.
        const auto &statefile = statefiles.front();
        saveEventlogOffsets(statefile, states);
    }

    return true;
}
