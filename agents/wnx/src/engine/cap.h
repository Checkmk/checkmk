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

enum class Mode { normal, forced };

// main API
void Install();    // normal installation of all files from the MSI
void ReInstall();  // forced installation of all files from the MSI

// support
bool InstallFileAsCopy(std::wstring_view filename,    // checkmk.dat
                       std::wstring_view target_dir,  // $CUSTOM_PLUGINS_PATH$
                       std::wstring_view source_dir,  // @root/install
                       Mode mode) noexcept;

bool NeedReinstall(const std::filesystem::path &Target,
                   const std::filesystem::path &Src);

using ProcFunc = bool (*)(const std::filesystem::path &TargetCap,
                          const std::filesystem::path &SrcCap);

bool ReinstallCaps(const std::filesystem::path &TargetCap,
                   const std::filesystem::path &SrcCap);

bool ReinstallIni(const std::filesystem::path &TargetIni,
                  const std::filesystem::path &SrcIni);

// data structures to use
enum class ProcMode { install, remove, list };

// valid eof is {empty, empty, true}
// valid NOT eod if {name, data, false}
using FileInfo = std::tuple<std::string, std::vector<char>, bool>;

// Main API to install and uninstall plugins cap
bool Process(const std::string CapFileName, ProcMode Mode,
             std::vector<std::wstring> &FilesLeftOnDisk);

// converts name in cap to name in actual environment
std::wstring ProcessPluginPath(const std::string &File);

// Low Level API
// Returns -1 is a bad value, not nice
// #TODO think over API
uint32_t ReadFileNameLength(std::ifstream &CapFile);
std::string ReadFileName(std::ifstream &CapFile, uint32_t Length);
std::vector<char> ReadFileData(std::ifstream &CapFile);
FileInfo ExtractFile(std::ifstream &CapFile);
bool StoreFile(const std::wstring &Name, const std::vector<char> &Data);

// idiotic API form thje past. Do not for what hell, but let it stay
bool CheckAllFilesWritable(const std::string &Directory);

}  // namespace cma::cfg::cap

#endif  // cap_h__
