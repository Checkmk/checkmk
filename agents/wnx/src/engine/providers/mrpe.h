// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

// Code and logic mirrors functionality of LA

#pragma once
#ifndef mrpe_h__
#define mrpe_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "Logger.h"
#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {
constexpr bool kParallelMrpe{false};
constexpr bool kMrpeRemoveAbsentFiles{false};

std::vector<std::string> TokenizeString(const std::string &val, int sub_match);

class MrpeEntry {
public:
    MrpeEntry(const std::string &run_as_user,  // only from cfg
              const std::string &cmd_line,     // parsed
              const std::string &exe_name,     // parsed
              const std::string &description)
        : run_as_user_(run_as_user)
        , command_line_(cmd_line)
        , exe_name_(exe_name)
        , description_(description) {}

    MrpeEntry(const std::string &run_as_user,  // only from cfg
              const std::string &value)
        : run_as_user_(run_as_user) {
        loadFromString(value);
    }

    bool add_age() const noexcept { return add_age_; }
    int cache_age_max() const noexcept { return cache_max_age_; }

    void loadFromString(const std::string &Value);
    std::string run_as_user_;
    std::string command_line_;
    std::string exe_name_;
    std::string description_;
    std::string full_path_name_;

private:
    // caching support
    int cache_max_age_{0};
    bool add_age_{false};
};

class MrpeCache {
public:
    struct Line {
        std::string data;
        std::chrono::steady_clock::time_point tp;
        int max_age{0};
        bool add_age{false};
    };

    enum class LineState { absent, ready, old };

    MrpeCache() = default;

    MrpeCache(const MrpeCache &) = delete;
    MrpeCache(MrpeCache &&) = delete;
    MrpeCache &operator=(const MrpeCache &) = delete;
    MrpeCache &operator=(MrpeCache &&) = delete;

    void createLine(std::string_view key, int max_age, bool add_age);
    bool updateLine(std::string_view key, std::string_view data);
    bool eraseLine(std::string_view key);

    std::tuple<std::string, LineState> getLineData(std::string_view key);

private:
    std::unordered_map<std::string, Line> cache_;
};

class MrpeProvider : public Asynchronous {
public:
    MrpeProvider() : Asynchronous(cma::section::kMrpe) {}

    MrpeProvider(const std::string_view &name, char separator)
        : Asynchronous(name, separator) {}

    void loadConfig() override;

    void updateSectionStatus() override;

    const auto entries() const noexcept { return entries_; }
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
    bool parseAndLoadEntry(const std::string &Entry);

private:
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
void AddCfgFileToEntries(const std::string &user,
                         const std::filesystem::path &path,
                         std::vector<MrpeEntry> &entries);
}  // namespace cma::provider

#endif  // mrpe_h__
