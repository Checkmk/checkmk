// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#include <yaml-cpp/yaml.h>

#include <vector>

#include "cma_core.h"

constexpr std::string_view RUN_FILE_EXTENSION = ".run";
constexpr std::string_view RUN_FILE_OLD_EXTENSION = ".run.old";
constexpr std::chrono::milliseconds TIME_TO_WAIT_BEFORE_KILL =
    std::chrono::milliseconds(5000);

namespace cma::cfg::extensions {
enum class Mode { yes, no, automatic };
struct Extension {
    std::string name;
    std::string binary;
    std::string command_line;
    Mode mode;
    std::filesystem::path run_file_;
};

std::vector<Extension> GetAll(YAML::Node node);
struct ProcessInfo {
    std::filesystem::path path;
    uint32_t pid;
    Extension extension;
};
std::vector<ProcessInfo> StartAll(const std::vector<Extension> &extensions);
void KillAll(const std::vector<ProcessInfo> &processes,
             const std::optional<std::chrono::milliseconds> &timeout);

/// searchs for predefined binary on path(case ignored)
/// - powershell
/// - powershell.exe
std::string FindBinary(std::string_view name);

class ExtensionsManager {
public:
    ExtensionsManager(const std::vector<Extension> &extensions,
                      std::optional<uint32_t> validate_period)
        : ExtensionsManager(extensions, validate_period,
                            TIME_TO_WAIT_BEFORE_KILL) {}
    ExtensionsManager(const std::vector<Extension> &extensions,
                      std::optional<uint32_t> validate_period,
                      const std::optional<std::chrono::milliseconds>
                          &time_to_wait_before_kill)
        : extensions_{extensions}
        , validate_period_(validate_period)
        , time_to_wait_before_kill_(time_to_wait_before_kill)
        , t_{&ExtensionsManager::thread_proc, this} {}
    ExtensionsManager(const ExtensionsManager &) = delete;
    ExtensionsManager &operator=(const ExtensionsManager &) = delete;
    ExtensionsManager(ExtensionsManager &&) = delete;
    ExtensionsManager &operator=(ExtensionsManager &&) = delete;

    ~ExtensionsManager();

    std::vector<ProcessInfo> processes() { return processes_; };

private:
    std::mutex mutex_;
    std::condition_variable cv_;
    bool stop_requested_{false};
    void thread_proc();
    std::vector<Extension> extensions_;
    std::optional<uint32_t> validate_period_;
    std::optional<std::chrono::milliseconds> time_to_wait_before_kill_;
    std::vector<ProcessInfo> processes_;
    std::jthread t_;
};

}  // namespace cma::cfg::extensions
