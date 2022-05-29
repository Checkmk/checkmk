// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef agent_controller_h__
#define agent_controller_h__
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string_view>

namespace YAML {
class Node;
}

namespace cma::ac {

// Should be synchronized with Rust code of controller
constexpr std::string_view kLegacyPullFile{"allow-legacy-pull"};
constexpr std::string_view kControllerFlagFile{"controller-flag"};
constexpr std::string_view kCmkAgentUnistall{"cmk_agent_uninstall.txt"};
constexpr std::string_view kCmkAgentMarkerNewDeprecated{
    "Check MK monitoring and management Service - "};
constexpr std::string_view kCmkAgentMarkerLatest{
    "Checkmk monitoring agent service - "};
constexpr std::string_view kCmdLineAsDaemon{"daemon"};
constexpr std::string_view kCmdLinePort{"-P"};
constexpr std::string_view kCmdLineChannel{"--agent-channel"};
constexpr std::string_view kCmdLineAllowedIp{"-A"};
constexpr std::string_view kCmdLineVersion{"-V"};
constexpr std::string_view kCmdLineStatus{"status --json"};
constexpr uint16_t kWindowsInternalServicePort{28250U};
constexpr uint16_t kWindowsInternalExePort{50002U};

std::filesystem::path GetController(const std::filesystem::path &service);
std::filesystem::path GetWorkController();
bool CreateTomlConfig(const std::filesystem::path &toml_file);
std::wstring BuildCommandLine(const std::filesystem::path &controller);
std::optional<uint32_t> StartAgentController();
bool KillAgentController();
bool DeleteControllerInBin();
std::string DetermineAgentCtlVersion();
std::string DetermineAgentCtlStatus();
bool IsRunController(const YAML::Node &node);
bool IsInLegacyMode();
void CreateControllerFlagFile();
bool IsControllerFlagFileExists();

std::filesystem::path LegacyPullFile();
std::filesystem::path ControllerFlagFile();
std::filesystem::path TomlConfigFile();

// config
uint16_t GetConfiguredAgentChannelPort(Modus modus);
bool GetConfiguredLocalOnly();
bool GetConfiguredCheck();
bool IsConfiguredEmergencyOnCrash();

/// To be called once when cap is installed
///
/// marker contains uninstall information
/// always remove marker file
/// controller_exists is determined by caller
/// creates controller-flag allow-pull-mode
/// According to https://jira.lan.tribe29.com/browse/CMK-10073
/// if !controler_exists
/// - does nothing
/// else
/// - creates legacy-pull if no controller flag
/// - create controller flag
///
void CreateArtifacts(const std::filesystem::path &marker,
                     bool controller_exists);
}  // namespace cma::ac

#endif  // agent_controller_h__
