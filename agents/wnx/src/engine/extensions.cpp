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

}  // namespace
std::vector<Extension> GetAll(YAML::Node node) {
    const auto x = GetNode(node, groups::kExtensions);
    if (x.IsMap()) {
        auto executions = GetNode(x, vars::kExtensionsExecution);
        std::vector<Extension> exts;
        std::set<std::string> names;
        for (auto &&entry : executions) {
            const auto name =
                GetVal<std::string>(entry, vars::kExecutionName, {});
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
    return {};
}

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
        if (tools::RunDetachedProcess(to_run)) {
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
