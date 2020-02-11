
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/logwatch_event.h"

#include <fmt/format.h>

#include <filesystem>
#include <limits>
#include <regex>
#include <string>
#include <tuple>

#include "cfg.h"
#include "cfg_engine.h"
#include "common/wtools.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogvista.h"
#include "logger.h"
#include "providers/logwatch_event_details.h"
#include "tools/_raii.h"

namespace cma::provider {

// trivial converter. kOff if LevelValue is not valid
// safe for nullptr and mixed case
cma::cfg::EventLevels LabelToEventLevel(std::string_view Level) {
    using namespace cma::cfg;

    if (Level.data() == nullptr) {
        XLOG::l(XLOG_FUNC + " parameter set to nullptr ");
        return cma::cfg::EventLevels::kOff;
    }

    std::string val(Level);
    cma::tools::StringLower(val);

    EventLevels levels[] = {EventLevels::kIgnore, EventLevels::kOff,
                            EventLevels::kAll, EventLevels::kWarn,
                            EventLevels::kCrit};

    for (auto level : levels) {
        if (val == ConvertLogWatchLevelToString(level)) return level;
    }

    XLOG::d("Key '{}' is not allowed, switching level to 'off'", val);
    return EventLevels::kOff;
}

void LogWatchEntry::init(std::string_view Name, std::string_view LevelValue,
                         bool Context) {
    name_ = Name;
    context_ = Context;
    level_ = LabelToEventLevel(LevelValue);

    loaded_ = true;
}

static std::pair<std::string, std::string> ParseLine(
    std::string_view Line) noexcept {
    auto name_body = cma::tools::SplitString(std::string(Line), ":");
    if (name_body.empty()) {
        XLOG::l("Bad entry '{}' in logwatch section ", Line);
        return {};
    }

    auto name = name_body[0];
    cma::tools::AllTrim(name);
    if (name.empty()) return {};

    if (name.back() == '\"' || name.back() == '\'') name.pop_back();
    if (name.empty()) return {};

    if (name.front() == '\"' || name.front() == '\'') name.erase(name.begin());
    cma::tools::AllTrim(name);  // this is intended
    if (name.empty()) {
        XLOG::d("Skipping empty entry '{}'", Line);
        return {};
    }

    auto body = name_body.size() > 1 ? name_body[1] : "";
    cma::tools::AllTrim(body);
    return {name, body};
}

bool LogWatchEntry::loadFromMapNode(const YAML::Node Node) noexcept {
    if (Node.IsNull() || !Node.IsDefined()) return false;
    if (!Node.IsMap()) return false;
    try {
        YAML::Emitter emit;
        emit << Node;
        return loadFrom(emit.c_str());
    } catch (const std::exception& e) {
        XLOG::l(
            "Failed to load logwatch entry from Node exception: '{}' in file '{}'",
            e.what(), wtools::ConvertToUTF8(cma::cfg::GetPathOfLoadedConfig()));
        return false;
    }
}
// For one-line encoding, example:
// - 'Application' : crit context
bool LogWatchEntry::loadFrom(std::string_view Line) noexcept {
    using namespace cma::cfg;
    if (Line.data() == nullptr || Line.empty()) {
        XLOG::t("Skipping logwatch entry with empty name");
        return false;
    }

    try {
        bool context = false;
        auto level = EventLevels::kOff;
        auto [name, body] = ParseLine(Line);
        if (name.empty()) return false;

        auto table = cma::tools::SplitString(std::string(body), " ");
        std::string level_string{vars::kLogWatchEvent_ParamDefault};
        if (table.size()) {
            level_string = table[0];
            cma::tools::AllTrim(level_string);
            if (table.size() > 1) {
                auto context_value = table[1];
                cma::tools::AllTrim(context_value);
                context = cma::tools::IsEqual(context_value, "context");
            }
        } else {
            XLOG::d("logwatch entry '{}' has no data, this is not normal",
                    name);
        }

        init(std::string(name), level_string, context);
        return true;
    } catch (const std::exception& e) {
        XLOG::l(
            "Failed to load logwatch entry '{}' exception: '{}' in file '{}'",
            std::string(Line), e.what(),
            wtools::ConvertToUTF8(cma::cfg::GetPathOfLoadedConfig()));
        return false;
    }
}

// returns count of loaded
void LogWatchEvent::loadConfig() {
    using namespace cma::cfg;
    send_all_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventSendall, true);
    evl_type_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventVistaApi, true)
            ? EvlType::vista
            : EvlType::classic;

    max_size_ = GetVal(groups::kLogWatchEvent, vars::kLogWatchEventMaxSize,
                       logwatch::kMaxSize);
    max_entries_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventMaxEntries,
               logwatch::kMaxEntries);
    max_line_length_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventMaxLineLength,
               logwatch::kMaxLineLength);
    timeout_ = GetVal(groups::kLogWatchEvent, vars::kLogWatchEventTimeout,
                      logwatch::kTimeout);

    if (!cma::evl::g_evt.module() || !cma::evl::g_evt.openLog) {
        XLOG::d(
            "Vista API requested in config, but support in OS is absent. Disabling...");
        evl_type_ = EvlType::classic;
    }
    const auto cfg = cma::cfg::GetLoadedConfig();
    int count = 0;
    try {
        const auto section = cfg[groups::kLogWatchEvent];

        // sanity checks:
        if (!section) {
            XLOG::t("'{}' section absent", groups::kLogWatchEvent);
            return;
        }

        if (!section.IsMap()) {
            XLOG::l("'{}' is not correct", groups::kLogWatchEvent);
            return;
        }

        // get array, on success, return it
        const auto log_array = section[vars::kLogWatchEventLogFile];
        if (!log_array) {
            XLOG::t("'{}' section has no '{}' member", groups::kLogWatchEvent,
                    vars::kLogWatchEventLogFile);
            return;
        }

        if (!log_array.IsSequence()) {
            XLOG::t("'{}' section has no '{}' member", groups::kLogWatchEvent,
                    vars::kLogWatchEventLogFile);
            return;
        }

        entries_.clear();
        bool default_found = false;
        for (auto& l : log_array) {
            entries_.push_back(LogWatchEntry());
            entries_.back().loadFromMapNode(l);
            if (entries_.back().loaded()) {
                ++count;
                if (entries_.back().name() == "*") {
                    default_found = true;
                    default_entry_ = entries_.size() - 1;
                }

            } else {
                if (!entries_.empty()) entries_.pop_back();
            }
        }
        if (!default_found) {
            // making default entry
            entries_.push_back(LogWatchEntry());
            entries_.back().init("*", "off", false);
            default_entry_ = entries_.size() - 1;
        }
        XLOG::l.t("Loaded [{}] entries in LogWatch", count);

    } catch (const std::exception& e) {
        XLOG::l(
            "CONFIG for '{}.{}' is seriously not valid, skipping. Exception {}. Loaded {} entries",
            groups::kLogWatchEvent, vars::kLogWatchEventLogFile, e.what(),
            count);
    }
}

namespace details {
// Example: line = "System|1234" provides {"System", 1234}
// gtest
State ParseStateLine(const std::string& Line) {
    auto tbl = cma::tools::SplitString(Line, "|");

    if (tbl.size() != 2 || tbl[0].empty() || tbl[1].empty()) {
        XLOG::l("State Line is not valid {}", Line);
        return {};
    }

    auto pos = cma::tools::ConvertToUint64(tbl[1]);
    if (pos.has_value()) return {tbl[0], pos.value(), false};

    XLOG::l("State Line has no valid pos {}", Line);
    return {};
}

// build big common state
// gtest [+]
StateVector LoadEventlogOffsets(const PathVector& statefiles,
                                bool ResetPosToNull) {
    for (const auto& fname : statefiles) {
        StateVector states;
        std::ifstream ifs(fname);
        std::string line;

        while (std::getline(ifs, line)) {
            if (line.empty()) continue;  // may happen at last line
            // remove trailing carriage return
            if (line.back() == '\n') line.pop_back();

            // build state from the text
            auto state = ParseStateLine(line);

            // check status
            if (state.name_.empty()) continue;

            if (ResetPosToNull) state.pos_ = 0;

            states.push_back(state);
        }

        std::sort(states.begin(), states.end(),
                  [](const auto& s1, const auto& s2) {
                      return cma::tools::IsLess(s1.name_, s2.name_);
                  });

        if (!states.empty()) {
            return states;
        }
    }

    return {};
}

void SaveEventlogOffsets(const std::string& FileName,
                         const StateVector& States) {
    {
        std::ofstream ofs(FileName);

        if (!ofs) {
            XLOG::l("Can't open file {} error {}", FileName, GetLastError());
            return;
        }

        for (const auto& state : States) {
            if (state.name_ == std::string("*")) continue;

            auto pos = state.pos_;

            ofs << state.name_ << "|" << pos << std::endl;
        }
    }
}
}  // namespace details

constexpr const char* S_EventLogRegPath =
    "SYSTEM\\CurrentControlSet\\Services\\Eventlog";

// updates presented flag or add to the States
void AddLogState(StateVector& states, bool from_config,
                 const std::string& log_name, SendMode send_mode) {
    for (auto& state : states) {
        if (cma::tools::IsEqual(state.name_, log_name)) {
            XLOG::t("Old event log '{}' found", log_name);

            state.setDefaults();
            state.in_config_ = from_config;
            state.presented_ = true;
            return;
        }
    }

    // new added
    uint64_t pos = send_mode == SendMode::all ? 0 : cma::cfg::kFromBegin;
    states.emplace_back(State(log_name, pos, true));
    states.back().in_config_ = from_config;
    XLOG::t("New event log '{}' added with pos {}", log_name, pos);
}

// main API to add config entries to the engine
void AddConfigEntry(StateVector& States, const LogWatchEntry& Log,
                    bool ResetToNull) {
    for (auto& state : States) {
        if (cma::tools::IsEqual(state.name_, Log.name())) {
            XLOG::t("Old event log '{}' found", Log.name());

            state.setDefaults();
            state.hide_context_ = !Log.context();
            state.level_ = Log.level();
            state.in_config_ = true;
            state.presented_ = true;
            return;
        }
    }

    // new added
    uint64_t pos = ResetToNull ? 0 : cma::cfg::kFromBegin;
    States.emplace_back(State(Log.name(), pos, true));
    States.back().in_config_ = true;
    States.back().level_ = Log.level();
    States.back().hide_context_ = !Log.context();
    XLOG::t("New event log '{}' added with pos {}", Log.name(), pos);
}

// Update States vector with log entries and Send All flags
// event logs are available
// returns count of processed Logs entries
int UpdateEventLogStates(StateVector& states, std::vector<std::string> logs,
                         SendMode send_mode) {
    for (auto& log : logs) {
        AddLogState(states, false, log, send_mode);
    };

    return static_cast<int>(logs.size());
}

std::vector<std::string> GatherEventLogEntriesFromRegistry() {
    return wtools::EnumerateAllRegistryKeys(S_EventLogRegPath);
}

bool IsEventLogInRegistry(std::string_view Name) {
    auto regs = GatherEventLogEntriesFromRegistry();
    bool found = false;
    for (auto& r : regs) {
        if (r == Name) return true;
    }
    return false;
}

std::optional<uint64_t> GetLastPos(EvlType type, std::string_view name) {
    if (type == EvlType::classic && !IsEventLogInRegistry(name)) return {};

    auto log =
        cma::evl::OpenEvl(wtools::ConvertToUTF16(name), type == EvlType::vista);

    if (!log) return {};
    if (!log->isLogValid()) return {};

    return log->getLastRecordId();
}

std::pair<uint64_t, std::string> DumpEventLog(cma::evl::EventLogBase& log,
                                              State state, LogWatchLimits lwl) {
    std::string out;
    int64_t count = 0;
    auto start = std::chrono::steady_clock::now();
    auto pos = cma::evl::PrintEventLog(
        log, state.pos_, state.level_, state.hide_context_,
        [&out, lwl, &count, start](const std::string& str) -> bool {
            if (lwl.max_line_length > 0 &&
                static_cast<int64_t>(str.length()) >= lwl.max_line_length) {
                out += str.substr(0, static_cast<size_t>(lwl.max_line_length));
                out += '\n';
            } else
                out += str;

            if (lwl.max_size > 0 &&
                static_cast<int64_t>(out.length()) >= lwl.max_size) {
                return false;
            }
            ++count;
            if (lwl.max_entries > 0 && count >= lwl.max_entries) return false;

            if (lwl.timeout > 0) {
                auto p = std::chrono::steady_clock::now();
                auto span =
                    std::chrono::duration_cast<std::chrono::seconds>(p - start);
                if (span.count() > lwl.timeout) return false;
            }

            return true;
        }

    );

    return {pos, out};
}

std::optional<std::string> ReadDataFromLog(EvlType type, State& state,
                                           LogWatchLimits lwl) {
    if (type == EvlType::classic && !IsEventLogInRegistry(state.name_)) {
        // we have to check registry, Windows always return success for
        // OpenLog for any even not existent log, but opens Application
        XLOG::d("Log '{}' not found in registry, try VistaApi ", state.name_);
        return {};
    }

    auto log = cma::evl::OpenEvl(wtools::ConvertToUTF16(state.name_),
                                 type == EvlType::vista);

    if (!log) return {};
    if (!log->isLogValid()) return {};

    if (state.pos_ == cma::cfg::kFromBegin) {
        // We just started monitoring this log.
        state.pos_ = log->getLastRecordId();
        return "";
    }

    // The last processed eventlog record will serve as previous state
    // (= saved offset) for the next call.
    auto [last_pos, worst_state] =
        cma::evl::ScanEventLog(*log, state.pos_, state.level_);

    if (worst_state < state.level_) {
        // nothing to report
        state.pos_ = last_pos;
        return "";
    }

    auto [pos, out] = DumpEventLog(*log, state, lwl);

    if (provider::config::G_SetLogwatchPosToEnd && last_pos > pos) {
        XLOG::l.t("Skipping logwatch pos from [{}] to [{}]", pos, last_pos);
        pos = last_pos;
    }

    state.pos_ = pos;
    return out;
}

LogWatchEntry GenerateDefaultValue() { return LogWatchEntry().withDefault(); }

bool LoadFromConfig(State& state, const LogWatchEntryVector& entries) noexcept {
    for (auto& config_entry : entries) {
        if (cma::tools::IsEqual(state.name_, config_entry.name())) {
            // found, check that param is not off
            state.hide_context_ = !config_entry.context();
            state.level_ = config_entry.level();
            state.in_config_ = true;
            return true;
        }
    }

    // check default entry
    return false;
}

void UpdateStatesByConfig(StateVector& states,
                          const LogWatchEntryVector& entries,
                          const LogWatchEntry* dflt) {
    LogWatchEntry default_entry = dflt ? *dflt : GenerateDefaultValue();

    // filtering states
    for (auto& s : states) {
        if (LoadFromConfig(s, entries)) continue;

        // not found - attempting to load default value
        s.hide_context_ = !default_entry.context();
        s.level_ = default_entry.level();

        // if default level isn't off, then we set entry as configured
        if (s.level_ != cfg::EventLevels::kOff) s.in_config_ = true;
    }
}

LogWatchLimits LogWatchEvent::getLogWatchLimits() const noexcept {
    // verified by gtest
    return {max_size_, max_line_length_, max_entries_, timeout_};
}

std::vector<std::filesystem::path> LogWatchEvent::makeStateFilesTable() const {
    namespace fs = std::filesystem;
    std::vector<fs::path> statefiles;
    fs::path state_dir = cfg::GetStateDir();
    auto ip_addr = ip();
    if (!ip_addr.empty()) {
        auto ip_fname = MakeStateFileName(kLogWatchEventStateFileName,
                                          kLogWatchEventStateFileExt, ip_addr);
        if (!ip_fname.empty()) statefiles.push_back(state_dir / ip_fname);
    }

    auto normal_fname = MakeStateFileName(kLogWatchEventStateFileName,
                                          kLogWatchEventStateFileExt);

    statefiles.push_back(state_dir / normal_fname);
    return statefiles;
}

std::string GenerateOutputFromStates(EvlType type, StateVector& states,
                                     LogWatchLimits lwl) {
    using namespace cma::cfg;

    std::string out;
    for (auto& state : states) {
        switch (state.level_) {
            case EventLevels::kOff:
                // updates position in state file for disabled log too
                {
                    auto pos = GetLastPos(type, state.name_);
                    state.pos_ = pos.has_value() ? *pos : 0;
                }
                [[fallthrough]];
            case EventLevels::kIgnore:
                // this is NOT log, just stupid entries in registry
                continue;

            default:
                if (state.in_config_) {
                    auto log_data = ReadDataFromLog(type, state, lwl);
                    if (log_data.has_value()) {
                        out += "[[[" + state.name_ + "]]]\n" + *log_data;
                    } else
                        out += "[[[" + state.name_ + ":missing]]]\n";
                } else {
                    // skipping
                    XLOG::d("Skipping log {}", state.name_);
                }
        }
    }

    return out;
}

std::string LogWatchEvent::makeBody() {
    using namespace cma::cfg;
    namespace fs = std::filesystem;

    XLOG::t(XLOG_FUNC + " entering");

    // The agent reads from a state file the record numbers
    // of the event logs up to which messages have
    // been processed. When no state information is available,
    // the eventlog is skipped to the end (unless the sendall config
    // option is used).
    auto statefiles = makeStateFilesTable();

    // creates states table from the file
    auto states =
        details::LoadEventlogOffsets(statefiles, send_all_);  // offsets stored

    // check by registry, which logs are presented
    auto logs = GatherEventLogEntriesFromRegistry();
    if (logs.size() == 0) {
        XLOG::l("Registry has nothing to logwatch. This is STRANGE");
    }
    UpdateEventLogStates(states, logs,
                         send_all_ ? SendMode::all : SendMode::normal);

    // 2) Register additional, configured logs that are not in registry.
    //    Note: only supported with vista API enabled.
    if (evl_type_ == EvlType::vista) {
        for (auto& e : entries_) {
            AddConfigEntry(states, e, send_all_);
        }
    }

    // now we have states list and want to mark all registered sources
    UpdateStatesByConfig(states, entries_, defaultEntry());

    // make string
    auto out = GenerateOutputFromStates(evl_type_, states, getLogWatchLimits());

    // The offsets are persisted in a statefile.
    // Always use the first available statefile name. In case of a
    // TCP/IP connection, this is the host-IP-specific statefile, and in
    // case of non-TCP (test / debug run etc.) the general
    // eventstate.txt.
    const auto& statefile = statefiles.front();
    details::SaveEventlogOffsets(statefile.u8string(), states);

    return out;
}

}  // namespace cma::provider
