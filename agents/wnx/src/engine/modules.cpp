//
//
// Support for the Windows Agent  modules
//
//

#include "stdafx.h"

#include "modules.h"

#include <fmt/format.h>

#include <filesystem>

#include "cfg.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"

namespace cma::cfg::modules {

void Module::reset() noexcept {
    name_.clear();
    exts_.clear();
    exec_.clear();
    dir_.clear();
}

[[nodiscard]] std::vector<Module> LoadFromConfig(const YAML::Node& yaml) {
    try {
        auto m = yaml[groups::kModules];

        // check enable
        auto enabled = GetVal(m, vars::kEnabled, true);
        if (!enabled) return {};

        // gather all modules in the table
        std::vector<Module> vec;
        auto module_array = GetArray<YAML::Node>(m, vars::kModulesTable);
        int index = 0;
        for (const auto& module_node : module_array) {
            Module m;
            ++index;
            if (!m.loadFrom(module_node) || !m.valid()) {
                XLOG::l.w("Skip module {}", index - 1);
                continue;
            }

            if (std::any_of(std::begin(vec), std::end(vec),
                            [m](const Module& vec_m) {
                                return vec_m.name() == m.name();
                            })) {
                XLOG::l.w("Skip module {} with duplicated name '{}'", index - 1,
                          m.name());
                continue;
            }

            vec.push_back(m);
        }
        XLOG::l.i("Processed [{}] modules", vec.size());
        return vec;

    } catch (const std::exception& e) {
        XLOG::l("Failed processing modules '{}'", e.what());
        return {};
    }

    return {};
}

[[nodiscard]] bool Module::loadFrom(const YAML::Node& node) {
    //
    //
    try {
        name_ = node[vars::kModulesName].as<std::string>();
        exec_ =
            wtools::ConvertToUTF16(node[vars::kModulesExec].as<std::string>());
        exts_ = GetArray<std::string>(node[vars::kModulesExts]);
        std::string dir;

        // dir is optional
        try {
            dir = node[vars::kModulesDir].as<std::string>();
        } catch (const std::exception& e) {
            XLOG::t("dir is missing or not valid, this is ok '{}'", e.what());
        }
        if (dir.empty()) dir = defaults::kModulesDir;
        dir_ = fmt::format(dir, name());

    } catch (const std::exception& e) {
        XLOG::l("failed loading module '{}'", e.what());
        reset();
        return false;
    }

    if (name().empty()) {
        XLOG::l("Name is absent or not valid");
        reset();
        return false;
    }
    return true;
}
}  // namespace cma::cfg::modules
