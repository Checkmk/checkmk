// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// engine to install/remove cap files

#ifndef cap_h__
#define cap_h__

#pragma once

#include <filesystem>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"

namespace cma::cfg::cap {

constexpr uint32_t kMaxAttemptsToStoreFile = 5;
constexpr size_t kMinimumProcessNameLength = 10;
constexpr std::string_view kAllowedExtension = ".EXE";

enum class Mode { normal, forced };

// main API
bool Install();    // normal installation of all files from the MSI
bool ReInstall();  // forced installation of all files from the MSI

// support
bool InstallFileAsCopy(std::wstring_view filename,    // checkmk.dat
                       std::wstring_view target_dir,  // $CUSTOM_PLUGINS_PATH$
                       std::wstring_view source_dir,  // @root/install
                       Mode mode);

bool NeedReinstall(const std::filesystem::path &Target,
                   const std::filesystem::path &Src);

using ProcFunc = bool (*)(const std::filesystem::path &TargetCap,
                          const std::filesystem::path &SrcCap);

bool ReinstallCaps(const std::filesystem::path &target_cap,
                   const std::filesystem::path &source_cap);

bool ReinstallYaml(const std::filesystem::path &bakery_yaml,
                   const std::filesystem::path &target_yaml,
                   const std::filesystem::path &source_yaml);

namespace details {
void UninstallYaml(const std::filesystem::path &bakery_yaml,
                   const std::filesystem::path &target_yaml);

void InstallYaml(const std::filesystem::path &bakery_yaml,
                 const std::filesystem::path &target_yaml,
                 const std::filesystem::path &source_yaml);
}  // namespace details

// data structures to use
enum class ProcMode { install, remove, list };

// valid eof is {empty, empty, true}
// valid NOT eod if {name, data, false}
using FileInfo = std::tuple<std::string, std::vector<char>, bool>;

// Main API to install and uninstall plugins cap
bool Process(const std::string &cap_name, ProcMode mode,
             std::vector<std::wstring> &files_left_on_disk);

// Secondary API to decompress plugins cap
bool ExtractAll(const std::string &cap_name, const std::filesystem::path &to);

// converts name in cap to name in actual environment
std::wstring ProcessPluginPath(const std::string &name);

// Low Level API
// Returns -1 is a bad value, not nice
// #TODO think over API
uint32_t ReadFileNameLength(std::ifstream &cap_file);
std::string ReadFileName(std::ifstream &cap_file, uint32_t length);
std::optional<std::vector<char>> ReadFileData(std::ifstream &cap_file);
FileInfo ExtractFile(std::ifstream &cap_file);
bool StoreFile(const std::wstring &name, const std::vector<char> &data);

[[nodiscard]] std::wstring GetProcessToKill(std::wstring_view name);
// we will try to kill the process with name of the executable if
// we cannot write to the file
[[nodiscard]] bool StoreFileAgressive(const std::wstring &name,
                                      const std::vector<char> &data,
                                      uint32_t attempts_count);

[[nodiscard]] bool IsStoreFileAgressive() noexcept;
[[nodiscard]] bool IsAllowedToKill(std::wstring_view proc_name);

// idiotic API form thje past. Do not for what hell, but let it stay
bool CheckAllFilesWritable(const std::string &directory);

// tgt,src
using PairOfPath = std::pair<std::filesystem::path, std::filesystem::path>;
PairOfPath GetExampleYmlNames();

PairOfPath GetInstallPair(std::wstring_view name);
}  // namespace cma::cfg::cap

#endif  // cap_h__
