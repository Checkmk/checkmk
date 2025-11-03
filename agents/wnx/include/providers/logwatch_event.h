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

template <typename T>
struct Interval {
    T lo;
    T hi;
};

/// If empty returns true for any value
template <typename T>
class IntervalSet {
public:
    explicit IntervalSet(std::vector<Interval<T>> intervals)
        : intervals_(std::move(intervals)) {}

    bool contains(const T &x) const {
        if (intervals_.empty()) {
            return false;
        }

        // attempt to find first not good interval
        auto it = std::upper_bound(intervals_.begin(), intervals_.end(), x,
                                   [](const T &value, const Interval<T> &iv) {
                                       return value < iv.lo;
                                   });
        if (it == intervals_.begin()) {
            return false;
        }
        // and step back if found
        --it;
        return it->lo <= x && x < it->hi;
    }

private:
    std::vector<Interval<T>> intervals_;
};

template <typename T>
class IntervalSetBuilder {
public:
    void add(T lo, T hi) {
        if (hi < lo) {
            intervals_.push_back({hi, lo});
        } else {
            intervals_.push_back({lo, hi});
        }
    }

    std::optional<IntervalSet<T>> build() {
        if (intervals_.empty()) {
            return std::nullopt;
        }
        std::sort(intervals_.begin(), intervals_.end(),
                  [](const Interval<T> &a, const Interval<T> &b) {
                      return a.lo < b.lo;
                  });

        std::vector<Interval<T>> merged;
        merged.push_back(intervals_.front());
        for (size_t i = 1; i < intervals_.size(); ++i) {
            auto &last = merged.back();
            const auto &cur = intervals_[i];
            if (cur.lo <= last.hi) {  // overlap or touch (inclusive)
                if (cur.hi > last.hi) last.hi = cur.hi;
            } else {
                merged.push_back(cur);
            }
        }

        return std::optional<IntervalSet<T>>(IntervalSet<T>(merged));
    }

private:
    std::vector<Interval<T>> intervals_;
};

class EventIdIntervals {
public:
    using Intervals = std::optional<IntervalSet<uint64_t>>;
    EventIdIntervals() = default;

    explicit EventIdIntervals(Intervals includes,
                              Intervals excludes = std::nullopt)
        : includes_(std::move(includes)), excludes_(std::move(excludes)) {}

    bool check(uint64_t id) const {
        // skip if present _and_ list contains id
        if (excludes_ && excludes_->contains(id)) {
            return false;
        }

        // if includes is present, then check it and return
        if (includes_) {
            return includes_->contains(id);
        }

        // either not in excludes and no includes - all good
        return true;
    }

private:
    Intervals includes_;
    Intervals excludes_;
};

class TagDualCollection {
public:
    using TagCollection = std::optional<std::vector<std::string>>;
    TagDualCollection() = default;

    explicit TagDualCollection(TagCollection includes,
                               TagCollection excludes = std::nullopt)
        : includes_(std::move(includes)), excludes_(std::move(excludes)) {}

    bool check(std::string_view name) const {
        // skip if present _and_ list contains id
        if (excludes_ &&
            std::ranges::any_of(*excludes_, [name](const auto &exclude) {
                return name == exclude;
            })) {
            return false;
        }

        // if includes is present, then check it and return
        if (includes_) {
            return std::ranges::any_of(*includes_, [name](const auto &include) {
                return name == include;
            });
        }

        // either not in excludes and no includes - all good
        return true;
    }

private:
    TagCollection includes_;
    TagCollection excludes_;
};

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
    LogWatchEntry(std::string_view name, std::string_view level_value,
                  cfg::EventContext context);

    static LogWatchEntry makeDefaultEntry() {
        return LogWatchEntry(
            "*", ConvertLogWatchLevelToString(cfg::EventLevels::kWarn),
            cfg::EventContext::with);
    }

    LogWatchEntry()
        : LogWatchEntry("",
                        ConvertLogWatchLevelToString(cfg::EventLevels::kOff),
                        cfg::EventContext::hide) {}

    [[nodiscard]] std::string name() const noexcept { return name_; }
    [[nodiscard]] cfg::EventContext context() const noexcept {
        return context_;
    }
    [[nodiscard]] cfg::EventLevels level() const noexcept { return level_; }

private:
    std::string name_;
    cfg::EventLevels level_{cfg::EventLevels::kOff};
    cfg::EventContext context_{cfg::EventContext::hide};
};

class IdsFilter {
public:
    explicit IdsFilter(std::string_view line);

    [[nodiscard]] bool checkId(uint64_t id) const noexcept {
        return intervals_.check(id);
    }
    [[nodiscard]] std::string name() const noexcept { return name_; }
    [[nodiscard]] EventIdIntervals intervals() const noexcept {
        return intervals_;
    }

private:
    std::string name_;
    EventIdIntervals intervals_;
};

class TagsFilter {
public:
    explicit TagsFilter(std::string_view line);

    [[nodiscard]] bool checkTag(std::wstring_view tag) const noexcept {
        return tag_dual_collection_.check(wtools::ToUtf8(tag));
    }
    [[nodiscard]] bool checkTag(std::string_view tag) const noexcept {
        return tag_dual_collection_.check(tag);
    }
    [[nodiscard]] std::string name() const noexcept { return name_; }
    [[nodiscard]] TagDualCollection tag_dual_collection() const noexcept {
        return tag_dual_collection_;
    }

private:
    std::string name_;
    TagDualCollection tag_dual_collection_;
};

enum class EvlType { classic, vista };

using LogWatchEntries = std::vector<LogWatchEntry>;
struct EventFilters {
    std::unordered_map<std::string, IdsFilter> id;
    std::unordered_map<std::string, TagsFilter> source;
};

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
    LogWatchEntries entries_;
    EventFilters event_filters_;
    size_t default_entry_ = 0;
    bool send_all_ = false;
    EvlType evl_type_ = EvlType::classic;
    evl::SkipDuplicatedRecords skip_{evl::SkipDuplicatedRecords::no};
    void loadSectionParameters();
    static std::optional<YAML::Node> readLogEntryArray(std::string_view name);
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
bool UpdateState(State &state, const LogWatchEntries &entries) noexcept;

std::pair<uint64_t, std::string> DumpEventLog(cma::evl::EventLogBase &log,
                                              const State &state,
                                              LogWatchLimits lwl,
                                              const EventFilters &filters);
// Fix Values in states according to the config
void UpdateStates(StateVector &states, const LogWatchEntries &entries,
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
                                           LogWatchLimits lwl,
                                           const EventFilters &filters);

std::string GenerateOutputFromStates(
    EvlType type, StateVector &states, LogWatchLimits lwl,
    const EventFilters &filters);  // by value(32 bytes is ok)

bool IsEventLogInRegistry(std::string_view name);

cfg::EventLevels LabelToEventLevel(std::string_view required_level);

// used for a testing /analyzing
struct RawLogWatchData {
    bool loaded_;
    std::string_view name_;
    cfg::EventLevels level_;
    cfg::EventContext context_;
};

std::optional<LogWatchEntry> LoadFromString(std::string_view line);
}  // namespace cma::provider

#endif  // LOGWATCH_EVENT_H
