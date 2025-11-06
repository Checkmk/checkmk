// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/logwatch_event.h"

#include <fmt/format.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <ranges>
#include <regex>
#include <string>

#include "common/wtools.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogvista.h"
#include "providers/logwatch_event_details.h"
#include "wnx/cfg.h"
#include "wnx/cfg_engine.h"
#include "wnx/logger.h"
namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace cma::provider {

// kOff if LevelValue is not valid safe for nullptr and mixed case
cfg::EventLevels LabelToEventLevel(std::string_view required_level) {
    using cfg::EventLevels;
    if (required_level.data() == nullptr) {
        XLOG::l(XLOG_FUNC + " parameter set to nullptr ");
        return EventLevels::kOff;
    }

    std::string val(required_level);
    tools::StringLower(val);

    constexpr std::array levels = {EventLevels::kIgnore, EventLevels::kOff,
                                   EventLevels::kAll, EventLevels::kWarn,
                                   EventLevels::kCrit};

    for (const auto level : levels) {
        if (val == ConvertLogWatchLevelToString(level)) {
            return level;
        }
    }

    XLOG::d("Key '{}' is not allowed, switching level to 'off'", val);
    return EventLevels::kOff;
}

LogWatchEntry::LogWatchEntry(std::string_view name,
                             std::string_view level_value,
                             cfg::EventContext context)
    : name_(name), context_(context), level_(LabelToEventLevel(level_value)) {}

namespace {
std::pair<std::string, std::string> ParseLine(std::string_view line) {
    auto name_body = tools::SplitString(std::string(line), ":");
    if (name_body.empty()) {
        XLOG::l("Bad entry '{}' in logwatch section ", line);
        return {};
    }

    auto name = name_body[0];
    tools::AllTrim(name);
    if (name.empty()) {
        return {};
    }

    if (name.back() == '\"' || name.back() == '\'') {
        name.pop_back();
    }
    if (name.empty()) {
        return {};
    }

    if (name.front() == '\"' || name.front() == '\'') {
        name.erase(name.begin());
    }
    tools::AllTrim(name);  // this is intended
    if (name.empty()) {
        XLOG::d("Skipping empty entry '{}'", line);
        return {};
    }

    auto body = name_body.size() > 1 ? name_body[1] : "";
    tools::AllTrim(body);
    return {name, body};
}

std::optional<std::string> ObtainString(const YAML::Node &node) {
    if (node.IsNull() || !node.IsDefined() || !node.IsMap()) {
        return std::nullopt;
    }

    try {
        YAML::Emitter emit;
        emit << node;
        return emit.c_str();
    } catch (const std::exception &e) {
        XLOG::l(
            "Failed to load logwatch entry from Node exception: '{}' in file '{}'",
            e.what(), wtools::ToUtf8(cfg::GetPathOfLoadedConfig()));
        return std::nullopt;
    }
}

std::optional<Interval<uint64_t>> ParseIdRange(std::string_view range) {
    auto pair = tools::SplitString(std::string(range), "-");
    if (pair.size() > 1) {
        auto lo = tools::ConvertToUint64(pair[0]);
        auto hi = tools::ConvertToUint64(pair[1]);
        if (lo.has_value() && hi.has_value()) {
            return Interval<uint64_t>{*lo, *hi + 1};
        }
    } else {
        auto val = tools::ConvertToUint64(pair[0]);
        if (val.has_value()) {
            return Interval<uint64_t>{*val, *val + 1};
        }
    }

    return std::nullopt;
}
}  // namespace

IdsFilter::IdsFilter(std::string_view line) {
    if (line.data() == nullptr || line.empty()) {
        XLOG::t("Skipping logwatch filter with empty name");
        return;
    }

    try {
        auto [name, body] = ParseLine(line);
        if (name.empty() || !body.contains(";;")) {
            return;
        }
        name_ = name;
        tools::StringLower(name_);

        IntervalSetBuilder<uint64_t> includes_builder;
        IntervalSetBuilder<uint64_t> excludes_builder;
        auto table = tools::SplitString(std::string(body), ";;", 2);
        auto includes = tools::SplitString(table[0], ";");
        for (const auto &i : includes) {
            const auto range = ParseIdRange(i);
            includes_builder.add(range->lo, range->hi);
        }
        if (table.size() > 1) {
            auto excludes = tools::SplitString(table[1], ";");
            for (const auto &i : excludes) {
                const auto range = ParseIdRange(i);
                excludes_builder.add(range->lo, range->hi);
            }
        }
        intervals_ = EventIdIntervals(includes_builder.build(),
                                      excludes_builder.build());

    } catch (const std::exception &e) {
        XLOG::l(
            "Failed to load logwatch ids entry '{}' exception: '{}' in file '{}'",
            std::string(line), e.what(),
            wtools::ToUtf8(cfg::GetPathOfLoadedConfig()));
    }
}

TagsFilter::TagsFilter(std::string_view line) {
    if (line.data() == nullptr || line.empty()) {
        XLOG::t("Skipping logwatch filter with empty name");
        return;
    }

    try {
        const auto [name, body] = ParseLine(line);
        if (name.empty() || !body.contains(";;")) {
            return;
        }
        name_ = name;
        tools::StringLower(name_);

        auto table = tools::SplitString(std::string(body), ";;", 2);
        auto i = tools::SplitString(table[0], ";");
        TagDualCollection::TagCollection includes =
            i.empty() ? std::nullopt : std::optional{i};
        auto e = table.size() > 1 ? tools::SplitString(table[1], ";")
                                  : std::vector<std::string>{};
        TagDualCollection::TagCollection excludes =
            e.empty() ? std::nullopt : std::optional{e};
        tag_dual_collection_ = TagDualCollection(includes, excludes);

    } catch (const std::exception &e) {
        XLOG::l(
            "Failed to load logwatch tags entry '{}' exception: '{}' in file '{}'",
            std::string(line), e.what(),
            wtools::ToUtf8(cfg::GetPathOfLoadedConfig()));
    }
}

// For one-line encoding, example:
// - 'Application' : crit context
std::optional<LogWatchEntry> LoadFromString(std::string_view line) {
    using cfg::EventLevels;
    if (line.data() == nullptr || line.empty()) {
        XLOG::t("Skipping logwatch entry with empty name");
        return std::nullopt;
    }

    try {
        auto context = cfg::EventContext::hide;
        auto [name, body] = ParseLine(line);
        if (name.empty()) {
            return std::nullopt;
        }

        auto table = tools::SplitString(std::string(body), " ");
        std::string level_string{cfg::vars::kLogWatchEvent_ParamDefault};
        if (!table.empty()) {
            level_string = table[0];
            tools::AllTrim(level_string);
            if (table.size() > 1) {
                auto context_value = table[1];
                tools::AllTrim(context_value);
                context = tools::IsEqual(context_value, "context")
                              ? cfg::EventContext::with
                              : cfg::EventContext::hide;
            }
        } else {
            XLOG::d("logwatch entry '{}' has no data, this is not normal",
                    name);
        }

        return LogWatchEntry(name, level_string, context);
    } catch (const std::exception &e) {
        XLOG::l(
            "Failed to load logwatch entry '{}' exception: '{}' in file '{}'",
            std::string(line), e.what(),
            wtools::ToUtf8(cfg::GetPathOfLoadedConfig()));
        return std::nullopt;
    }
}
namespace {
std::vector<IdsFilter> ProcessEventIds(
    const std::optional<YAML::Node> &log_ids) {
    if (!log_ids.has_value()) {
        return {};
    }
    std::vector<IdsFilter> filters;
    for (const auto &l : *log_ids) {
        const auto line = ObtainString(l);
        if (line.has_value()) {
            auto id = IdsFilter(*line);
            filters.emplace_back(std::move(id));
        }
    }
    return filters;
}

std::vector<TagsFilter> ProcessEventTags(
    const std::optional<YAML::Node> &log_tags) {
    if (!log_tags.has_value()) {
        return {};
    }
    std::vector<TagsFilter> filters;
    for (const auto &l : *log_tags) {
        const auto line = ObtainString(l);
        if (line.has_value()) {
            auto tag = TagsFilter(*line);
            filters.emplace_back(std::move(tag));
        }
    }
    return filters;
}
}  // namespace

void LogWatchEvent::loadConfig() {
    loadSectionParameters();
    initLogwatchClustersMap();
    size_t count = 0;
    try {
        auto log_array = readLogEntryArray(cfg::vars::kLogWatchEventLogFile);
        if (!log_array.has_value()) {
            return;
        }
        count = processLogEntryArray(*log_array);
        setupDefaultEntry();
        XLOG::d.t("Loaded [{}] entries in LogWatch", count);
        event_filters_.id.clear();
        auto filter_ids = readLogEntryArray(cfg::vars::kLogWatchEventFilterIds);
        auto ids = ProcessEventIds(filter_ids);
        for (const auto &i : ids) {
            event_filters_.id.insert_or_assign(i.name(), i);
        }

        event_filters_.source.clear();
        auto filter_sources =
            readLogEntryArray(cfg::vars::kLogWatchEventFilterSources);
        auto sources = ProcessEventTags(filter_sources);
        for (const auto &s : sources) {
            event_filters_.source.insert_or_assign(s.name(), s);
        }

        event_filters_.user.clear();
        auto filter_users =
            readLogEntryArray(cfg::vars::kLogWatchEventFilterUsers);
        auto users = ProcessEventTags(filter_users);
        for (const auto &s : users) {
            event_filters_.user.insert_or_assign(s.name(), s);
        }

    } catch (const std::exception &e) {
        XLOG::l(
            "CONFIG for '{}.{}' is seriously not valid, skipping. Exception {}. Loaded {} entries",
            cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchEventLogFile,
            e.what(), count);
    }
}

void LogWatchEvent::loadSectionParameters() {
    using cfg::GetVal;
    send_all_ = GetVal(cfg::groups::kLogWatchEvent,
                       cfg::vars::kLogWatchEventSendall, true);
    evl_type_ = GetVal(cfg::groups::kLogWatchEvent,
                       cfg::vars::kLogWatchEventVistaApi, true)
                    ? EvlType::vista
                    : EvlType::classic;

    skip_ = GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchEventSkip,
                   false)
                ? evl::SkipDuplicatedRecords::yes
                : evl::SkipDuplicatedRecords::no;

    max_size_ =
        GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchEventMaxSize,
               cfg::logwatch::kMaxSize);
    max_entries_ =
        GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchEventMaxEntries,
               cfg::logwatch::kMaxEntries);
    max_line_length_ = GetVal(cfg::groups::kLogWatchEvent,
                              cfg::vars::kLogWatchEventMaxLineLength,
                              cfg::logwatch::kMaxLineLength);
    timeout_ =
        GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchEventTimeout,
               cfg::logwatch::kTimeout);

    if (!evl::IsEvtApiAvailable()) {
        XLOG::d(
            "Vista API requested in config, but support in OS is absent. Disabling...");
        evl_type_ = EvlType::classic;
    }
}

std::optional<YAML::Node> LogWatchEvent::readLogEntryArray(
    std::string_view name) {
    const auto section_opt = getLogwatchSection();
    if (!section_opt.has_value()) {
        return {};
    }
    const auto &logwatch_section = *section_opt;

    // get array, on success, return it
    const auto log_array = logwatch_section[name];
    if (!log_array) {
        XLOG::t("'{}' section has no '{}' member", cfg::groups::kLogWatchEvent,
                name);
        return {};
    }

    if (!log_array.IsSequence()) {
        XLOG::t("'{}' section has no '{}' member", cfg::groups::kLogWatchEvent,
                name);
        return {};
    }
    return log_array;
}

size_t LogWatchEvent::processLogEntryArray(const YAML::Node &log_array) {
    size_t count{0U};
    entries_.clear();
    for (const auto &l : log_array) {
        const auto line = ObtainString(l);
        if (line.has_value()) {
            auto lwe = LoadFromString(*line);
            if (lwe) {
                ++count;
                entries_.emplace_back(std::move(*lwe));
            }
        }
    }

    return count;
}

std::optional<YAML::Node> LogWatchEvent::getLogwatchSection() {
    const auto cfg = cfg::GetLoadedConfig();
    const auto section = cfg[cfg::groups::kLogWatchEvent];
    if (!section || !section.IsDefined() || !section.IsMap()) {
        XLOG::t("getLogwatchSection: '{}' section is absent or not correct",
                cfg::groups::kLogWatchEvent);
        return {};
    }
    return section;
}

LogwatchClusterMap LogWatchEvent::parseClustersMap(
    const YAML::Node &clusters_node) {
    if (!clusters_node || !clusters_node.IsMap()) {
        return {};
    }

    LogwatchClusterMap clusters_map;
    clusters_map.reserve(clusters_node.size());

    // Not possible to use range-based loop with structured binding as
    // YAML::Node doesn't support it yet.
    // Update in case YAML::Node starts providing such interface.
    for (const auto &cluster : clusters_node) {
        auto cluster_name = cluster.first.as<std::string>();
        const auto &ip_list_node = cluster.second;

        // Add cluster to the map even if it has no IPs
        if (!ip_list_node || !ip_list_node.IsSequence()) {
            clusters_map.try_emplace(cluster_name);
            continue;
        }

        std::vector<std::string> ip_addresses;
        ip_addresses.reserve(ip_list_node.size());

        std::ranges::transform(ip_list_node, std::back_inserter(ip_addresses),
                               [](const YAML::Node &ip_node) {
                                   return ip_node.as<std::string>();
                               });

        clusters_map.try_emplace(std::move(cluster_name),
                                 std::move(ip_addresses));
    }

    return clusters_map;
}

void LogWatchEvent::initLogwatchClustersMap() {
    const auto section_opt = getLogwatchSection();
    if (!section_opt.has_value()) {
        return;
    }
    const auto &logwatch_section = *section_opt;

    const auto clusters = logwatch_section[cfg::vars::kLogWatchClusters];
    if (!clusters || !clusters.IsMap()) {
        XLOG::t(
            "initLogwatchClustersMap: '{}' section has no '{}' member or is not a valid map",
            cfg::groups::kLogWatchEvent, cfg::vars::kLogWatchClusters);
        return;
    }

    clusters_ = parseClustersMap(clusters);
}

bool LogWatchEvent::isCurrentIpInCluster(
    const std::string &cluster_name) const {
    const auto it = clusters_.find(cluster_name);
    if (it == clusters_.end()) {
        return false;
    }

    const auto &current_ip = ip();
    if (current_ip.empty()) {
        return false;
    }

    return std::ranges::contains(it->second, current_ip);
}

namespace {
std::optional<size_t> FindLastEntryWithName(const LogWatchEntries &entries,
                                            std::string_view name) {
    auto found = rs::find_if(entries.rbegin(), entries.rend(),
                             [name](auto e) { return e.name() == name; });
    return found == entries.rend()
               ? std::optional<size_t>{}
               : entries.size() - 1 - std::distance(entries.rbegin(), found);
}
}  // namespace

void LogWatchEvent::setupDefaultEntry() {
    auto offset = FindLastEntryWithName(entries_, "*");
    default_entry_ = offset.has_value() ? *offset : addDefaultEntry();
}

size_t LogWatchEvent::addDefaultEntry() {
    entries_.emplace_back(LogWatchEntry("*", "off", cfg::EventContext::hide));
    return entries_.size() - 1;
}

namespace details {
// Example: line = "System|1234" provides {"System", 1234}
State ParseStateLine(const std::string &line) {
    auto tbl = tools::SplitString(line, "|");

    if (tbl.size() != 2 || tbl[0].empty() || tbl[1].empty()) {
        XLOG::l("State Line is not valid {}", line);
        return {};
    }

    auto pos = tools::ConvertToUint64(tbl[1]);
    if (pos.has_value()) {
        return {tbl[0], pos.value(), false};
    }

    XLOG::l("State Line has no valid pos {}", line);
    return {};
}

// build big common state
StateVector LoadEventlogOffsets(const PathVector &state_files,
                                bool reset_pos_to_null) {
    for (const auto &fname : state_files) {
        StateVector states;
        std::ifstream ifs(fname);
        std::string line;

        while (std::getline(ifs, line)) {
            if (line.empty()) {
                continue;
            }
            // remove trailing carriage return
            if (line.back() == '\n') {
                line.pop_back();
            }

            // build state from the text
            auto state = ParseStateLine(line);

            // check status
            if (state.name_.empty()) {
                continue;
            }

            if (reset_pos_to_null) {
                state.pos_ = 0;
            }

            states.push_back(state);
        }

        rs::sort(states, [](const auto &s1, const auto &s2) {
            return tools::IsLess(s1.name_, s2.name_);
        });

        if (!states.empty()) {
            return states;
        }
    }

    return {};
}

auto x() {
    std::string_view s1 = "a";
    std::string_view s2 = "a";
    return s1 < s2;
}

void SaveEventlogOffsets(const std::string &file_name,
                         const StateVector &states) {
    {
        std::ofstream ofs(file_name);

        if (!ofs) {
            XLOG::l("Can't open file '{}' error [{}]", file_name,
                    ::GetLastError());
            return;
        }

        for (const auto &state : states) {
            if (state.name_ == "*") {
                continue;
            }
            ofs << state.name_ << "|" << state.pos_ << std::endl;
        }
    }
}
}  // namespace details

constexpr const char *g_event_log_reg_path =
    R"(SYSTEM\CurrentControlSet\Services\Eventlog)";

// updates presented flag or add to the States
void AddLogState(StateVector &states, bool from_config,
                 const std::string &log_name, SendMode send_mode) {
    for (auto &state : states) {
        if (tools::IsEqual(state.name_, log_name)) {
            XLOG::t("Old event log '{}' found", log_name);

            state.setDefaults();
            state.in_config_ = from_config;
            state.presented_ = true;
            return;
        }
    }

    // new added
    uint64_t pos = send_mode == SendMode::all ? 0 : cfg::kFromBegin;
    states.emplace_back(log_name, pos, true);
    states.back().in_config_ = from_config;
    XLOG::t("New event log '{}' added with pos {}", log_name, pos);
}

// main API to add config entries to the engine
void AddConfigEntry(StateVector &states, const LogWatchEntry &log_entry,
                    bool reset_to_null) {
    auto found = rs::find_if(states, [&](auto s) {
        return tools::IsEqual(s.name_, log_entry.name());
    });
    if (found != states.end()) {
        XLOG::t("Old event log '{}' found", log_entry.name());
        found->setDefaults();
        found->context_ = log_entry.context();
        found->level_ = log_entry.level();
        found->in_config_ = true;
        found->presented_ = true;
        return;
    }

    // new added
    uint64_t pos = reset_to_null ? 0 : cfg::kFromBegin;
    states.emplace_back(log_entry.name(), pos, true);
    states.back().in_config_ = true;
    states.back().level_ = log_entry.level();
    states.back().context_ = log_entry.context();
    XLOG::t("New event log '{}' added with pos {}", log_entry.name(), pos);
}

// Update States vector with log entries and Send All flags
// event logs are available
// returns count of processed Logs entries
int UpdateEventLogStates(StateVector &states,
                         const std::vector<std::string> &logs,
                         SendMode send_mode) {
    for (const auto &log : logs) {
        AddLogState(states, false, log, send_mode);
    }

    return static_cast<int>(logs.size());
}

std::vector<std::string> GatherEventLogEntriesFromRegistry() {
    return wtools::EnumerateAllRegistryKeys(g_event_log_reg_path);
}

bool IsEventLogInRegistry(std::string_view name) {
    auto regs = GatherEventLogEntriesFromRegistry();
    return std::ranges::any_of(
        regs, [name](const std::string &r) { return r == name; });
}

std::optional<uint64_t> GetLastPos(EvlType type, std::string_view name) {
    if (type == EvlType::classic && !IsEventLogInRegistry(name)) return {};

    auto log =
        evl::OpenEvl(wtools::ConvertToUtf16(name), type == EvlType::vista);

    if (log && log->isLogValid()) {
        return log->getLastRecordId();
    }

    return {};
}

namespace {
void PrintEvent(LogWatchLimits lwl, std::string &out,
                const std::string_view str) {
    if (lwl.max_line_length > 0 &&
        static_cast<int64_t>(str.length()) >= lwl.max_line_length) {
        out += str.substr(0, static_cast<size_t>(lwl.max_line_length));
        out += '\n';
    } else {
        out += str;
    }
}

bool TooMuch(LogWatchLimits lwl, const std::string &out, int64_t &count) {
    if (lwl.max_size > 0 &&
        static_cast<int64_t>(out.length()) >= lwl.max_size) {
        return true;
    }
    ++count;
    if (lwl.max_entries > 0 && count >= lwl.max_entries) {
        return true;
    }
    return false;
}

bool TooLong(LogWatchLimits lwl,
             std::chrono::time_point<std::chrono::steady_clock> start) {
    if (lwl.timeout > 0) {
        auto p = std::chrono::steady_clock::now();
        auto span = std::chrono::duration_cast<std::chrono::seconds>(p - start);
        if (span.count() > lwl.timeout) {
            return true;
        }
    }
    return false;
}

template <typename T>
std::optional<T> findWithDefault(const std::unordered_map<std::string, T> &m,
                                 std::string_view key) {
    auto it = m.find(std::string{key});
    if (it != m.end()) {
        return it->second;
    }
    return key == "*" ? std::nullopt : findWithDefault(m, "*");
}

bool RecordAllowed(const std::string_view log_file_name,
                   const evl::EventLogRecordBase *record,
                   const EventFilters &filters) {
    std::string name{log_file_name};
    tools::StringLower(name);

    if (auto ret = findWithDefault(filters.id, name); ret.has_value()) {
        if (!ret->checkId(record->eventId())) {
            return false;
        }
    }

    if (auto ret = findWithDefault(filters.source, name); ret.has_value()) {
        if (!ret->checkTag(record->source())) {
            return false;
        }
    }

    if (auto ret = findWithDefault(filters.user, name); ret.has_value()) {
        auto rec_user =
            wtools::FindUserName(record->sid()).value_or(std::wstring{});
        return ret->checkTag(rec_user);
    }

    return true;
}
}  // namespace

std::pair<uint64_t, std::string> DumpEventLog(evl::EventLogBase &log,
                                              const State &state,
                                              LogWatchLimits lwl,
                                              const EventFilters &filters) {
    std::string out;
    int64_t count = 0;
    auto start = std::chrono::steady_clock::now();
    auto pos = evl::PrintEventLog(
        log, state.pos_, state.level_, state.context_, lwl.skip,
        [&out, lwl, &count, start](const std::string &str) {
            PrintEvent(lwl, out, str);
            return !TooMuch(lwl, out, count) && !TooLong(lwl, start);
        },
        [&filters, &state](const evl::EventLogRecordBase *record) {
            return RecordAllowed(state.name_, record, filters);
        });

    return {pos, out};
}

std::optional<std::string> ReadDataFromLog(EvlType type, State &state,
                                           LogWatchLimits lwl,
                                           const EventFilters &filters) {
    if (type == EvlType::classic && !IsEventLogInRegistry(state.name_)) {
        // we have to check registry, Windows always return success for
        // OpenLog for any even not existent log, but opens Application
        XLOG::d("Log '{}' not found in registry, try VistaApi ", state.name_);
        return {};
    }

    auto log = evl::OpenEvl(wtools::ConvertToUtf16(state.name_),
                            type == EvlType::vista);

    if (!log || !log->isLogValid()) {
        return {};
    }

    if (state.pos_ == cfg::kFromBegin) {
        // We just started monitoring this log.
        state.pos_ = log->getLastRecordId();
        return "";
    }

    // The last processed eventlog record will serve as previous state
    // (= saved offset) for the next call.
    auto [last_pos, worst_state] =
        evl::ScanEventLog(*log, state.pos_, state.level_);

    if (worst_state < state.level_) {
        // nothing to report
        state.pos_ = last_pos;
        return "";
    }

    auto [pos, out] = DumpEventLog(*log, state, lwl, filters);

    if (provider::config::g_set_logwatch_pos_to_end && last_pos > pos) {
        XLOG::d.t("Skipping logwatch pos from [{}] to [{}]", pos, last_pos);
        pos = last_pos;
    }

    state.pos_ = pos;
    return out;
}

LogWatchEntry GenerateDefaultValue() {
    return LogWatchEntry::makeDefaultEntry();
}

bool UpdateState(State &state, const LogWatchEntries &entries) noexcept {
    for (const auto &config_entry : entries) {
        if (tools::IsEqual(state.name_, config_entry.name())) {
            state.context_ = config_entry.context();
            state.level_ = config_entry.level();
            state.in_config_ = true;
            return true;
        }
    }

    return false;
}

void UpdateStates(StateVector &states, const LogWatchEntries &entries,
                  const LogWatchEntry *dflt) {
    LogWatchEntry default_entry =
        dflt != nullptr ? *dflt : GenerateDefaultValue();

    // filtering states
    for (auto &s : states) {
        if (UpdateState(s, entries)) {
            continue;
        }

        // not found - attempting to load default value
        s.context_ = default_entry.context();
        s.level_ = default_entry.level();

        // if default level isn't off, then we set entry as configured
        if (s.level_ != cfg::EventLevels::kOff) {
            s.in_config_ = true;
        }
    }
}

LogWatchLimits LogWatchEvent::getLogWatchLimits() const noexcept {
    return {.max_size = max_size_,
            .max_line_length = max_line_length_,
            .max_entries = max_entries_,
            .timeout = timeout_,
            .skip = skip_};
}

std::vector<fs::path> LogWatchEvent::makeStateFilesTable() const {
    const fs::path state_dir = cfg::GetStateDir();
    std::vector<fs::path> state_files;

    const auto create_state_file = [&state_dir](std::string_view identifier =
                                                    "") {
        auto filename = identifier.empty()
                            ? MakeStateFileName(kLogWatchEventStateFileName,
                                                kLogWatchEventStateFileExt)
                            : MakeStateFileName(kLogWatchEventStateFileName,
                                                kLogWatchEventStateFileExt,
                                                std::string_view{identifier});

        return filename.empty() ? std::nullopt
                                : std::make_optional(state_dir / filename);
    };

    // Priority 1: Check for cluster-specific state file
    if (const auto cluster_file =
            rs::find_if(clusters_,
                        [this](const auto &cluster) {
                            return isCurrentIpInCluster(cluster.first);
                        });
        cluster_file != clusters_.end()) {
        if (auto cluster_file_path = create_state_file(cluster_file->first)) {
            state_files.push_back(cluster_file_path.value());
        }
    }

    // Priority 2: Check for IP-specific state file
    if (auto ip_addr = ip(); !ip_addr.empty()) {
        if (auto single_ip_file_path = create_state_file(ip_addr)) {
            state_files.push_back(single_ip_file_path.value());
        }
    }

    // Priority 3: Default state file
    if (auto default_file_path = create_state_file()) {
        state_files.push_back(default_file_path.value());
    }

    return state_files;
}

std::optional<IdsFilter> FindIds(std ::string_view name,
                                 std::vector<IdsFilter> &ids) {
    if (auto it = rs::find_if(
            ids, [name](const IdsFilter &f) { return f.name() == name; });
        it != ids.end()) {
        return *it;  // copy
    }
    return std::nullopt;
}

std::string GenerateOutputFromStates(EvlType type, StateVector &states,
                                     LogWatchLimits lwl,
                                     const EventFilters &filters) {
    std::string out;
    for (auto &state : states) {
        switch (state.level_) {
            case cfg::EventLevels::kOff:
                // updates position in state file for disabled log too
                state.pos_ = GetLastPos(type, state.name_).value_or(0);
                [[fallthrough]];
            case cfg::EventLevels::kIgnore:
                // this is NOT log, just stupid entries in registry
                continue;

            case cfg::EventLevels::kAll:
            case cfg::EventLevels::kWarn:
            case cfg::EventLevels::kCrit:
                if (state.in_config_) {
                    auto log_data = ReadDataFromLog(type, state, lwl, filters);
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
    if (logs.empty()) {
        XLOG::l("Registry has nothing to logwatch. This is STRANGE");
    }
    UpdateEventLogStates(states, logs,
                         send_all_ ? SendMode::all : SendMode::normal);

    // 2) Register additional, configured logs that are not in registry.
    //    Note: only supported with vista API enabled.
    if (evl_type_ == EvlType::vista) {
        for (const auto &e : entries_) {
            AddConfigEntry(states, e, send_all_);
        }
    }

    // now we have states list and want to mark all registered sources
    UpdateStates(states, entries_, defaultEntry());

    // make string
    auto out = GenerateOutputFromStates(evl_type_, states, getLogWatchLimits(),
                                        event_filters_);

    // The offsets are persisted in a statefile.
    // Always use the first available statefile name. In case of a cluster -
    // it is state file with cluster name,
    // in case of single-IP address connection over TCP/IP connection,
    // this is the host-IP-specific statefile, and in
    // case of non-TCP (test / debug run etc.) the general
    // eventstate.txt.
    const auto &statefile = statefiles.front();
    details::SaveEventlogOffsets(wtools::ToUtf8(statefile.wstring()), states);

    return out;
}

}  // namespace cma::provider
