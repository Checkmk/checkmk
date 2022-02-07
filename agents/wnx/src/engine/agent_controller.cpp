
#include "stdafx.h"

#include "agent_controller.h"

#include <filesystem>
#include <iosfwd>

#include "cfg.h"
#include "common/cfg_yaml.h"
#include "common/cma_yml.h"
#include "common/wtools.h"

namespace fs = std::filesystem;

namespace cma::ac {
bool IsRunController(const YAML::Node &node) {
    auto controller = cma::yml::GetNode(node, std::string{cfg::groups::kSystem},
                                        std::string{cfg::vars::kController});
    return cfg::GetVal(controller, cfg::vars::kControllerRun, false);
}

bool IsUseLegacyMode(const YAML::Node &node) {
    auto controller = cma::yml::GetNode(node, std::string{cfg::groups::kSystem},
                                        std::string{cfg::vars::kController});
    return cfg::GetVal(controller, cfg::vars::kControllerLegacyPull, false);
}

fs::path GetController(const fs::path &service) {
    auto controller = service;
    controller.replace_filename(cfg::files::kAgentCtl);
    return controller;
}

bool StartAgentController(const fs::path &service) {
    if (!cma::IsService()) {
        return false;
    }

    auto controller = GetController(service);
    wtools::AppRunner ar;
    auto proc_id = ar.goExecAsDetached(controller.wstring() + L" daemon");
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]", controller,
                  proc_id);
        return true;
    } else {
        XLOG::l("Agent controller '{}' failed to start", controller);
        return false;
    }
}

bool KillAgentController() {
    if (cma::IsService()) {
        return wtools::KillProcess(cfg::files::kAgentCtl, 1);
    }
    return false;
}

/// Creates/Deletes file in agent-user dir to satisfy controller requirements
void EnableLegacyMode(bool enable) {
    auto file_name = fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile;
    if (enable) {
        std::ofstream ofs(file_name.u8string());
        ofs << "Created by Windows agent";
    } else {
        std::error_code ec;
        fs::remove(file_name, ec);
    }
}

}  // namespace cma::ac
