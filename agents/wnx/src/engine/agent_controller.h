// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef agent_controller_h__
#define agent_controller_h__
#include <cstdint>
#include <filesystem>
#include <string_view>

namespace YAML {
class Node;
}

namespace cma::ac {

// Should be synchronized with Rust code of controller
constexpr std::string_view kLegacyPullFile{"allow-legacy-pull"};
constexpr std::string_view kCmdLineAsDaemon{"daemon"};
constexpr std::string_view kCmdLinePort{"-P"};
constexpr std::string_view kCmdLineAllowedIp{"-A"};
constexpr std::string_view kCmdLineVersion{"-V"};
constexpr uint16_t windows_internal_port{50001};

std::filesystem::path GetController(const std::filesystem::path &service);
std::filesystem::path GetWorkController();
std::wstring BuildCommandLine(const std::filesystem::path &controller);
bool StartAgentController(const std::filesystem::path &service);
bool KillAgentController(const std::filesystem::path &service);
std::string DetermineAgentCtlVersion();
bool IsRunController(const YAML::Node &node);
bool IsInLegacyMode();
void CreateLegacyModeFile();
}  // namespace cma::ac

#endif  // agent_controller_h__
