//
//
// Support for the Windows Agent  extensions
//
//

#include "stdafx.h"

#include "wnx/extensions.h"

#include <filesystem>
#include <set>
#include <string>
#include <vector>

#include "common/cfg_yaml.h"
#include "tools/_process.h"
#include "wnx/logger.h"

namespace fs = std::filesystem;
using namespace std::string_literals;

namespace cma::cfg::extensions {
namespace {
Mode ToMode(std::string_view mode) {
    std::string m{mode};
    tools::StringLower(m);
    if (m == "no") {
        return Mode::no;
    }
    if (m == "yes") {
        return Mode::yes;
    }
    if (m == "auto") {
        return Mode::automatic;
    }
    XLOG::t("Bad mode value {}, fallback to no", m);
    return Mode::no;
}

std::string FindBinary(std::string_view name) {
    if (tools::IsEqual(name, "powershell") ||
        tools::IsEqual(name, "powershell.exe")) {
        auto found = wtools::ToUtf8(cma::FindPowershellExe());
        return found.empty() ? std::string{name} : found;
    }
    return std::string{name};
}

std::vector<Extension> GatherExtensions(const YAML::Node &group) {
    auto executions = GetNode(group, vars::kExtensionsExecution);
    std::vector<Extension> exts;
    std::set<std::string> names;
    for (auto &&entry : executions) {
        const auto name = GetVal<std::string>(entry, vars::kExecutionName, {});
        if (names.contains(name)) {
            XLOG::t("duplicated name in extensions {}", name);
            continue;
        }
        names.emplace(name);

        const auto binary =
            GetVal<std::string>(entry, vars::kExecutionBinary, "");
        const auto command_line =
            GetVal<std::string>(entry, vars::kExecutionCmdLine, "");
        auto mode = GetVal<std::string>(entry, vars::kExecutionRun, "");
        exts.emplace_back(Extension{.name = name,
                                    .binary = FindBinary(binary),
                                    .command_line = command_line,
                                    .mode = ToMode(mode)});
    }
    return exts;
}

}  // namespace
std::vector<Extension> GetAll(YAML::Node node) {
    const auto group = GetNode(node, groups::kExtensions);
    if (group.IsMap() && GetVal(group, vars::kEnabled, false)) {
        return GatherExtensions(group);
    }
    return {};
}

namespace {
/// Do not have DETACHED_PROCESS flag: powershell can't be executed with
/// DETACHED_PROCESS
std::optional<uint32_t> RunExtension(const std::wstring &command) {
    STARTUPINFOW si = {};
    memset(&si, 0, sizeof si);
    si.cb = sizeof STARTUPINFO;
    si.dwFlags |= STARTF_USESTDHANDLES;  // SK: not sure with this flag

    PROCESS_INFORMATION pi = {};
    memset(&pi, 0, sizeof pi);

    if (std::wstring c{command};
        ::CreateProcessW(nullptr,   // stupid windows want null here
                         c.data(),  // win32!
                         nullptr,   // security attribute
                         nullptr,   // thread attribute
                         FALSE,     // no handle inheritance
                         CREATE_NEW_PROCESS_GROUP,  // Creation Flags
                         nullptr,                   // environment
                         nullptr,                   // current directory
                         &si, &pi) == TRUE) {
        uint32_t pid = ::GetProcessId(pi.hProcess);
        tools::ClosePi(pi);
        return pid;
    }
    return {};
}

std::optional<ProcessInfo> StartExtension(const Extension &extension) {
    XLOG::l.i("Agent extension '{}' to be processed", extension.name);
    if (extension.binary.empty() || extension.mode == Mode::no) {
        return {};
    }

    fs::path path{ReplacePredefinedMarkers(extension.binary)};
    if (std::error_code ec;
        !fs::exists(path, ec) && (extension.mode != Mode::yes)) {
        XLOG::l.i("'{}' not found, skipping", path);
        return {};
    }

    auto to_run = path.wstring();

    if (!extension.command_line.empty()) {
        to_run += L" "s + wtools::ConvertToUtf16(extension.command_line);
    }
    if (const auto pid = RunExtension(to_run); pid.has_value()) {
        XLOG::l.i("Agent extension '{}' started, pid is {}",
                  wtools::ToUtf8(to_run), *pid);
        return ProcessInfo{path, *pid, extension};
    } else {
        XLOG::l("Agent extension '{}' failed to start", wtools::ToUtf8(to_run));
        return {};
    }
}
}  // namespace

std::vector<ProcessInfo> StartAll(const std::vector<Extension> &extensions) {
    std::vector<ProcessInfo> started;
    for (const auto &extension : extensions) {
        auto ret = StartExtension(extension);
        if (ret.has_value()) {
            started.emplace_back(*ret);
        }
    }
    return started;
}

void KillAll(const std::vector<ProcessInfo> &processes) {
    XLOG::l.i("Killing Agent extensions");
    for (auto &&[path, pid, _] : processes) {
        wtools::KillProcessesByPathEndAndPid(path, pid);
    }
}

void ValidateAndRestart(std::vector<ProcessInfo> &processes) {
    for (auto &process : processes) {
        if (!wtools::FindProcessByPathEndAndPid(process.path, process.pid)) {
            XLOG::l.i("Agent extensions {} is dead", process.extension.name);
            const auto ret = StartExtension(process.extension);
            if (ret.has_value()) {
                process.pid = ret->pid;
                XLOG::l.i("Agent extensions {} is restarted",
                          process.extension.name);
            }
            XLOG::l.i("Agent extensions {} failed to restart",
                      process.extension.name);
        }
    }
}

}  // namespace cma::cfg::extensions
