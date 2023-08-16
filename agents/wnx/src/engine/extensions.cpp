//
//
// Support for the Windows Agent  extensions
//
//

#include "stdafx.h"

#include "extensions.h"

#include <set>

#include "common/cfg_yaml.h"

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
std::vector<Extension> GetExtensions(YAML::Node node) {
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

}  // namespace cma::cfg::extensions
