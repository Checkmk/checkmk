//
//
// Support for the Windows Agent  extensions
//
//

#include "stdafx.h"

#include "extensions.h"

#include <filesystem>
#include <set>
#include <string>
#include <vector>

#include "common/cfg_yaml.h"
#include "logger.h"
#include "tools/_process.h"

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
}  // namespace

std::vector<ProcessInfo> StartAll(const std::vector<Extension> &extensions) {
    std::vector<ProcessInfo> started;
    for (auto &&[name, binary, command_line, mode] : extensions) {
        XLOG::l.i("Agent extension '{}' to be processed", name);
        if (binary.empty() || mode == Mode::no) {
            continue;
        }

        fs::path path{ReplacePredefinedMarkers(binary)};
        if (std::error_code ec; !fs::exists(path, ec) && (mode != Mode::yes)) {
            XLOG::l.i("'{}' not found, skipping", path);
            continue;
        }

        auto to_run = path.wstring();

        if (!command_line.empty()) {
            to_run += L" "s + wtools::ConvertToUtf16(command_line);
        }
        if (auto pid = RunExtension(to_run); pid.has_value()) {
            XLOG::l.i("Agent extension '{}' started, pid is {}",
                      wtools::ToUtf8(to_run), *pid);
            started.emplace_back(path, *pid);
        } else {
            XLOG::l("Agent extension '{}' failed to start",
                    wtools::ToUtf8(to_run));
        }
    }
    return started;
}

void KillAll(const std::vector<ProcessInfo> &processes) {
    XLOG::l.i("Killing Agent extensions");
    for (auto &&[path, pid] : processes) {
        wtools::KillProcessesByPathEndAndPid(path, pid);
    }
}

}  // namespace cma::cfg::extensions
