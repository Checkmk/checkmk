
// provides basic api to start and stop service
#include "stdafx.h"

#include <filesystem>
#include <limits>
#include <regex>
#include <string>
#include <tuple>

#include "fmt/format.h"

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "cfg.h"

#include "logger.h"

#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogvista.h"

#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"

namespace cma::provider {

void LogWatchEntry::init(const std::string& Name, const std::string& LevelValue,
                         bool Context) {
    using namespace cma::cfg;
    name_ = Name;
    context_ = Context;

    if (LevelValue == "off")
        level_ = cma::cfg::EventLevels::kOff;
    else if (LevelValue == "all")
        level_ = cma::cfg::EventLevels::kAll;
    else if (LevelValue == "warn")
        level_ = cma::cfg::EventLevels::kWarn;
    else if (LevelValue == "crit")
        level_ = cma::cfg::EventLevels::kCrit;
    else
        level_ = cma::cfg::EventLevels::kOff;

    loaded_ = true;
}

bool LogWatchEntry::loadFrom(const YAML::Node Node) {
    using namespace cma::cfg;
    if (!Node.IsMap()) {
        XLOG::l("Bad node in logwatch");
        return false;
    }
    std::string name;
    bool context = false;

    try {
        auto name = Node[vars::kLogWatchEvent_Name].as<std::string>();
        auto level_string =
            Node[vars::kLogWatchEvent_Level].as<std::string>("off");
        auto context = Node[vars::kLogWatchEvent_Context].as<bool>(false);
        if (name.empty()) {
            return false;
        }
        init(name, level_string, context);
        return true;
    } catch (const std::exception& e) {
        XLOG::l("Failed to load node {} {} {} 'exception: {} in file{}'", name,
                level(), context, e.what(),
                wtools::ConvertToUTF8(cma::cfg::GetPathOfLoadedConfig()));
        return false;
    }
}

// returns count of loaded
void LogWatchEvent::loadConfig() {
    using namespace cma::cfg;
    send_all_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventSendall, true);
    vista_api_ =
        GetVal(groups::kLogWatchEvent, vars::kLogWatchEventVistaApi, true);
    if (!cma::evl::g_evt.module() || !cma::evl::g_evt.openLog) {
        XLOG::d(
            "Vista API requested in config, but support in OS is absent. Disabling...");
        vista_api_ = false;
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
            entries_.back().loadFrom(l);
            if (entries_.back().loaded()) {
                ++count;
                if (entries_.back().name() == "*") {
                    default_found = true;
                    default_entry_ = entries_.size() - 1;
                }

            } else
                entries_.pop_back();
        }
        if (!default_found) {
            // making default entry
            entries_.push_back(LogWatchEntry());
            entries_.back().init("*", "off", false);
            default_entry_ = entries_.size() - 1;
        }
        XLOG::d("Loaded {} entries in LogWatch", count);

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
            if (state.name_ != std::string("*"))
                ofs << state.name_ << "|" << state.pos_ << std::endl;
        }
    }
}
}  // namespace details

constexpr const char* S_EventLogRegPath =
    "SYSTEM\\CurrentControlSet\\Services\\Eventlog";

// updates presented flag or add to the States
void AddLogState(StateVector& States, bool FromConfig,
                 const std::string LogName, bool ResetPosToNull) {
    for (auto& state : States) {
        if (cma::tools::IsEqual(state.name_, LogName)) {
            XLOG::t("Old event log '{}' found", LogName);

            state.setDefaults();
            state.in_config_ = FromConfig;
            state.presented_ = true;
            return;
        }
    }

    // new added
    uint64_t pos = ResetPosToNull ? 0 : cma::cfg::kInitialPos;
    States.emplace_back(State(LogName, pos, true));
    States.back().in_config_ = FromConfig;
    XLOG::t("New event log '{}' added with pos {}", LogName, pos);
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
    uint64_t pos = ResetToNull ? 0 : cma::cfg::kInitialPos;
    States.emplace_back(State(Log.name(), pos, true));
    States.back().in_config_ = true;
    States.back().level_ = Log.level();
    States.back().hide_context_ = !Log.context();
    XLOG::t("New event log '{}' added with pos {}", Log.name(), pos);
}

// Update States vector with log entries and Send All flags
// event logs are available
// returns count of processed Logs entries
int UpdateEventLogStates(StateVector& States, std::vector<std::string> Logs,
                         bool SendAll) {
    for (auto& log : Logs) {
        AddLogState(States, false, log, SendAll);
    };
    return static_cast<int>(Logs.size());
}

std::vector<std::string> GatherEventLogEntriesFromRegistry() {
    return wtools::EnumerateAllRegistryKeys(S_EventLogRegPath);
}

bool IsEventLogInRegistry(const std::string Name) {
    auto regs = GatherEventLogEntriesFromRegistry();
    bool found = false;
    for (auto& r : regs) {
        if (r == Name) return true;
    }
    return false;
}

std::string ReadDataFromLog(bool VistaApi, State& St, bool& LogExists) {
    LogExists = false;

    if (!VistaApi && !IsEventLogInRegistry(St.name_)) {
        // we have to check registry, Windows always return success for OpenLog
        // for any even not existent log, but opens Application
        XLOG::d("Log '{}' not found in registry, try VistaApi ", St.name_);
        return {};
    }

    auto log = cma::evl::OpenEvl(wtools::ConvertToUTF16(St.name_), VistaApi);

    if (!log) return {};

    LogExists = log->isLogValid();
    if (!LogExists) return {};

    if (St.pos_ == cma::cfg::kInitialPos) {
        // We just started monitoring this log.
        St.pos_ = log->getLastRecordId();
        return {};
    } else {
        // The last processed eventlog record will serve as previous state
        // (= saved offset) for the next call.
        auto [last_pos, worst_state] =
            cma::evl::ScanEventLog(*log, St.pos_, St.level_);

        if (worst_state < St.level_) {
            // nothing to report
            St.pos_ = last_pos;
            return {};
        }

        auto [pos, str] =
            cma::evl::PrintEventLog(*log, St.pos_, St.level_, St.hide_context_);
        St.pos_ = pos;
        return str;
    }
}

void UpdateStatesByConfig(StateVector& States,
                          const LogWatchEntryVector& ConfigEntries,
                          const LogWatchEntry* Default) {
    // filtering states
    for (auto& s : States) {
        bool found = false;

        for (auto& config_entry : ConfigEntries) {
            if (cma::tools::IsEqual(s.name_, config_entry.name())) {
                // found, check that param is not off
                s.hide_context_ = !config_entry.context();
                s.level_ = config_entry.level();
                s.in_config_ = true;
                found = true;
                break;
            }
        }

        // check default entry
        if (found) continue;

        // not found - attempting to load default value
        if (Default) {
            s.hide_context_ = Default->context();
            s.level_ = Default->level();
        }
    }
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

std::string GenerateOutputFromStates(bool VistaApi, StateVector& States) {
    std::string out;
    for (auto& state : States) {
        if (state.level_ == cma::cfg::EventLevels::kOff) continue;
#if 0
        // This Legacy Agent mode AB says this is NOT valid approach
        if (state.presented_) {
            out += "[[[" + state.name_ + "]]]\n";
            out += ReadDataFromLog(state);
        } else {
            out += "[[[" + state.name_ + ":missing]]]\n";
        }
#else
        // According to AB
        if (state.in_config_) {
            bool valid_log = false;
            std::string log_data = ReadDataFromLog(VistaApi, state, valid_log);
            if (valid_log) {
                out += "[[[" + state.name_ + "]]]\n" + log_data;
            } else
                out += "[[[" + state.name_ + ":missing]]]\n";
        } else {
            // skipping
            XLOG::d("Skipping log {}", state.name_);
        }
#endif
    }

    return out;
}

std::string LogWatchEvent::makeBody() const {
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
    UpdateEventLogStates(states, logs, send_all_);

    // 2) Register additional, configured logs that are not in registry.
    //    Note: only supported with vista API enabled.
    if (vista_api_) {
        for (auto& e : entries_) {
            AddConfigEntry(states, e, send_all_);
        }
    }

    // now we have states list and want to mark all registered sources
    UpdateStatesByConfig(states, entries_, defaultEntry());

    // make string
    std::string out = GenerateOutputFromStates(vista_api_, states);

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
