// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef LOGWATCH_EVENT_H
#define LOGWATCH_EVENT_H

#include <filesystem>
#include <string>
#include <string_view>
#include <utility>

#include "common/cfg_info.h"
#include "eventlog/eventlogbase.h"
#include "providers/internal.h"
#include "wnx/cfg_engine.h"
#include "wnx/section_header.h"

namespace cma::provider {
constexpr std::string_view kLogWatchEventStateFileName{"eventstate"};
constexpr std::string_view kLogWatchEventStateFileExt{".txt"};

struct LogWatchLimits {
    int64_t max_size;
    int64_t max_line_length;
    int64_t max_entries;
    int64_t timeout;
    evl::SkipDuplicatedRecords skip;
};

struct State {
    State(std::string name, uint64_t pos, bool new_found)
        : name_(std::move(name)), pos_(pos), presented_(new_found) {
        setDefaults();
    }
    State() = default;
    explicit State(const std::string &name) : State(name, 0, true) {}

    // #IMPORTANT default set of the level and context set MINIMAL
    void setDefaults() {
        level_ = cfg::EventLevels::kCrit;    // #IMPORTANT
        context_ = cfg::EventContext::hide;  // #IMPORTANT
    }
    std::string name_;
    uint64_t pos_{0};
    bool presented_{false};  // either in registry or in config
    bool in_config_{false};  // config described

    cfg::EventLevels level_{cfg::EventLevels::kAll};
    cfg::EventContext context_{cfg::EventContext::with};
};

using StateVector = std::vector<State>;

class LogWatchEntry {
public:
    bool loadFromMapNode(const YAML::Node &node);
    bool loadFrom(std::string_view line);
    void init(std::string_view name, std::string_view level_value,
              cfg::EventContext context);
    LogWatchEntry &withDefault() {
        init("*", ConvertLogWatchLevelToString(cfg::EventLevels::kWarn),
             cfg::EventContext::with);
        return *this;
    }

    [[nodiscard]] std::string name() const noexcept {
        return loaded_ ? name_ : std::string{};
    }
    [[nodiscard]] cfg::EventContext context() const noexcept {
        return context_;
    }
    [[nodiscard]] bool loaded() const noexcept { return loaded_; }
    [[nodiscard]] cfg::EventLevels level() const noexcept { return level_; }

private:
    std::string name_;
    cfg::EventLevels level_{cfg::EventLevels::kOff};
    cfg::EventContext context_{cfg::EventContext::hide};
    bool loaded_{false};
};

enum class EvlType { classic, vista };

using LogWatchEntryVector = std::vector<LogWatchEntry>;

class LogWatchEvent final : public Asynchronous {
public:
    LogWatchEvent() : Asynchronous(cma::section::kLogWatchEventName) {}

    LogWatchEvent(const std::string &name, char separator)
        : Asynchronous(name, separator) {}

    void loadConfig() override;

    const auto &entries() const { return entries_; }
    const LogWatchEntry *defaultEntry() const {
        if (default_entry_ < entries().size()) {
            return &entries_[default_entry_];
        }
        XLOG::l("This can't happen index is {} size is {} ", default_entry_,
                entries().size());
        return nullptr;
    }
    std::vector<std::filesystem::path> makeStateFilesTable() const;

    bool sendAll() const { return send_all_; }
    EvlType evlType() const { return evl_type_; }
    LogWatchLimits getLogWatchLimits() const noexcept;

    std::string makeBody() override;

private:
    LogWatchEntryVector entries_;
    size_t default_entry_ = 0;
    bool send_all_ = false;
    EvlType evl_type_ = EvlType::classic;
    evl::SkipDuplicatedRecords skip_{evl::SkipDuplicatedRecords::no};
    void loadSectionParameters();
    static std::optional<YAML::Node> readLogEntryArray();
    /// returns count of found entries
    size_t processLogEntryArray(const YAML::Node &log_array);
    void setupDefaultEntry();
    size_t addDefaultEntry();

    // limits block
    int64_t max_size_ = cfg::logwatch::kMaxSize;
    int64_t max_line_length_ = cfg::logwatch::kMaxLineLength;
    int64_t max_entries_ = cfg::logwatch::kMaxEntries;
    int64_t timeout_ = cfg::logwatch::kTimeout;
};

// ***********************************************************************
// Internal API
// ***********************************************************************
// Read from registry registered sources and add them to the states vector
std::vector<std::string> GatherEventLogEntriesFromRegistry();
enum class SendMode { all, normal };

// Update States vector with log entries and Send All flags
// event logs are available
// returns count of processed Logs entries
int UpdateEventLogStates(StateVector &states,
                         const std::vector<std::string> &logs,
                         SendMode send_mode);

LogWatchEntry GenerateDefaultValue();

std::optional<uint64_t> GetLastPos(EvlType type, std::string_view name);
bool UpdateState(State &state, const LogWatchEntryVector &entries) noexcept;

std::pair<uint64_t, std::string> DumpEventLog(cma::evl::EventLogBase &log,
                                              const State &state,
                                              LogWatchLimits lwl);
// Fix Values in states according to the config
void UpdateStates(StateVector &states, const LogWatchEntryVector &entries,
                  const LogWatchEntry *dflt);
// manual adding: two things possible
// 1. added brand new
// 2. existing marked as presented_
void AddLogState(StateVector &states, bool from_config,
                 const std::string &log_name, SendMode send_mode);

// to use for load entries of config
void AddConfigEntry(StateVector &states, const LogWatchEntry &log_entry,
                    bool reset_to_null);

// returns output from log and set value validity
// nothing when log is absent
// empty string when no more to read
std::optional<std::string> ReadDataFromLog(EvlType type, State &state,
                                           LogWatchLimits lwl);

std::string GenerateOutputFromStates(
    EvlType type, StateVector &states,
    LogWatchLimits lwl);  // by value(32 bytes is ok)

bool IsEventLogInRegistry(std::string_view name);

cfg::EventLevels LabelToEventLevel(std::string_view required_level);

// used for a testing /analyzing
struct RawLogWatchData {
    bool loaded_;
    std::string_view name_;
    cfg::EventLevels level_;
    cfg::EventContext context_;
};

}  // namespace cma::provider

#endif  // LOGWATCH_EVENT_H
