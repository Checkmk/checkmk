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
                                    .binary = binary,
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
bool RunExtension(const std::wstring &command) {
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
        tools::ClosePi(pi);
        return true;
    }
    return false;
}
}  // namespace

std::vector<fs::path> StartAll(const std::vector<Extension> &extensions) {
    std::vector<fs::path> started;
    for (auto &&[name, binary, command_line, mode] : extensions) {
        XLOG::l.i("Agent extension '{}' to be processed", name);
        if (binary.empty() || mode == Mode::no) {
            continue;
        }

        fs::path path{ReplacePredefinedMarkers(binary)};
        if (std::error_code ec; !fs::exists(path, ec)) {
            continue;
        }

        auto to_run = path.wstring();
        if (!command_line.empty()) {
            to_run += L" "s + wtools::ConvertToUtf16(command_line);
        }
        if (RunExtension(to_run)) {
            XLOG::l.i("Agent extension '{}' started", wtools::ToUtf8(to_run));
            started.emplace_back(path);
        } else {
            XLOG::l("Agent extension '{}' failed to start",
                    wtools::ToUtf8(to_run));
        }
    }
    return started;
}

void KillAll(const std::vector<std::filesystem::path> &paths) {
    XLOG::l.i("Killing Agent extensions");
    for (auto &&path : paths) {
        wtools::KillProcessesByFullPath(path);
    }
}

}  // namespace cma::cfg::extensions
