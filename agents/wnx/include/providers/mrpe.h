// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef MRPE_H
#define MRPE_H

#include <filesystem>
#include <string>
#include <string_view>
#include <utility>

#include "wnx/cma_core.h"
#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {
constexpr bool kParallelMrpe{false};
constexpr bool kMrpeRemoveAbsentFiles{false};

std::vector<std::string> TokenizeString(const std::string &val, int sub_match);

class MrpeEntry {
public:
    MrpeEntry(std::string run_as_user,  // only from cfg
              std::string cmd_line,     // parsed
              std::string exe_name,     // parsed
              std::string description)
        : run_as_user_(std::move(run_as_user))
        , command_line_(std::move(cmd_line))
        , exe_name_(std::move(exe_name))
        , description_(std::move(description)) {}

    MrpeEntry(std::string run_as_user,  // only from cfg
              const std::string &value)
        : run_as_user_(std::move(run_as_user)) {
        loadFromString(value);
    }

    void loadFromString(const std::string &value);
    std::string run_as_user_;
    std::string command_line_;
    std::string exe_name_;
    std::string description_;
    std::string full_path_name_;
    std::optional<int> caching_interval_;
};

class MrpeCache {
public:
    struct Line {
        std::string data;
        std::chrono::steady_clock::time_point tp;
    };

    enum class LineState { absent, ready, old };

    MrpeCache() = default;

    MrpeCache(const MrpeCache &) = delete;
    MrpeCache(MrpeCache &&) = delete;
    MrpeCache &operator=(const MrpeCache &) = delete;
    MrpeCache &operator=(MrpeCache &&) = delete;

    void createLine(std::string_view key);
    bool updateLine(std::string_view key, std::string_view data);

    std::tuple<std::string, LineState> getLineData(std::string_view key,
                                                   int max_age);

private:
    std::unordered_map<std::string, Line> cache_;
};

class MrpeProvider final : public Asynchronous {
public:
    MrpeProvider() : Asynchronous(cma::section::kMrpe) {}

    MrpeProvider(std::string_view name, char separator)
        : Asynchronous(name, separator) {}

    void loadConfig() override;

    const auto &entries() const noexcept { return entries_; }
    const auto &includes() const noexcept { return includes_; }
    const auto &checks() const noexcept { return checks_; }

protected:
    std::string makeBody() override;

    // sub API
    void parseConfig();
    void addParsedConfig();  // includes_ and checks_ -> entries_

    // internal
    void addParsedChecks();    // checks_ -> entries_
    void addParsedIncludes();  // includes_ -> entries_
    bool parseAndLoadEntry(const std::string &entry);

private:
    void loadTimeout();
    std::vector<MrpeEntry> entries_;

    std::vector<std::string> checks_;    // "check = ...."
    std::vector<std::string> includes_;  // "include = ......"

    MrpeCache cache_;
};

// Important internal API as set of free functions
std::pair<std::string, std::filesystem::path> ParseIncludeEntry(
    const std::string &entry);

void FixCrCnForMrpe(std::string &str);
std::string ExecMrpeEntry(const MrpeEntry &entry,
                          std::chrono::milliseconds timeout);
std::string MrpeEntryResult(const MrpeEntry &entry, MrpeCache &cache,
                            std::chrono::milliseconds timeout);
void AddCfgFileToEntries(const std::string &user,
                         const std::filesystem::path &path,
                         std::vector<MrpeEntry> &entries);
}  // namespace cma::provider

#endif  // MRPE_H
