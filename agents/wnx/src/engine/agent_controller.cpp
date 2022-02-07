
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

fs::path GetWorkController() {
    return fs::path{cfg::GetUserBinDir()} / cfg::files::kAgentCtl;
}

namespace {
std::pair<fs::path, fs::path> ServiceName2TargetName(const fs::path &service) {
    return {GetController(service), GetWorkController()};
}

fs::path CopyControllerToBin(const fs::path &service) {
    const auto [src, tgt] = ServiceName2TargetName(service);
    std::error_code ec;
    fs::copy(src, tgt, fs::copy_options::overwrite_existing, ec);
    if (ec.value() == 0) {
        return tgt;
    }
    XLOG::l("error copying controller from '{}' to '{}' [{}]", src, tgt,
            ec.value());

    auto tgt_sav = tgt;
    try {
        tgt_sav.replace_extension(".sav");
    } catch (const std::exception &e) {
        XLOG::l("error renaming controller '{}'", e.what());
    }

    fs::rename(tgt, tgt_sav, ec);
    fs::copy(src, tgt, fs::copy_options::overwrite_existing, ec);
    if (ec.value() == 0) {
        return tgt;
    }
    XLOG::l("error copying controller from '{}' to '{}' [{}]", src, tgt,
            ec.value());
    return {};
}

void DeleteControllerInBin(const fs::path &service) {
    const auto [_, tgt] = ServiceName2TargetName(service);
    std::error_code ec;
    if (fs::exists(tgt, ec)) {
        fs::remove(tgt, ec);
        if (ec.value() != 0) {
            XLOG::l("error deleting controller", ec.value());
        }
    }
}
}  // namespace

bool StartAgentController(const fs::path &service) {
    if (!cma::IsService()) {
        return false;
    }

    auto controller_name = CopyControllerToBin(service);
    if (controller_name.empty()) {
        XLOG::l("can't copy controller");
        return false;
    }

    wtools::AppRunner ar;
    auto proc_id = ar.goExecAsDetached(controller_name.wstring() + L" daemon");
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]", controller_name,
                  proc_id);
        return true;
    } else {
        XLOG::l("Agent controller '{}' failed to start", controller_name);
        return false;
    }
}

bool KillAgentController(const fs::path &service) {
    if (cma::IsService()) {
        auto ret = wtools::KillProcess(cfg::files::kAgentCtl, 1);
        DeleteControllerInBin(service);
        return ret;
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
