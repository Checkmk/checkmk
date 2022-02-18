
#include "stdafx.h"

#include "agent_controller.h"

#include <filesystem>
#include <iosfwd>
#include <iostream>

#include "cfg.h"
#include "common/cfg_yaml.h"
#include "common/cma_yml.h"
#include "common/wtools.h"

namespace fs = std::filesystem;
using namespace std::chrono_literals;

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

/// returns true if controller files DOES NOT exist
bool DeleteControllerInBin(const fs::path &service) {
    const auto [_, tgt] = ServiceName2TargetName(service);
    std::error_code ec;
    if (!fs::exists(tgt, ec)) {
        return true;
    }

    fs::remove(tgt, ec);
    return !fs::exists(tgt, ec);
}
}  // namespace

std::wstring BuildCommandLine(const fs::path &controller) {
    auto port =
        cfg::GetVal(cfg::groups::kGlobal, cfg::vars::kPort, cfg::kMainPort);
    auto only_from =
        cfg::GetInternalArray(cfg::groups::kGlobal, cfg::vars::kOnlyFrom);
    std::string allowed_ip;
    if (!only_from.empty()) {
        allowed_ip = " " + std::string{kCmdLineAllowedIp};
        for (const auto &a : only_from) {
            allowed_ip += " " + a;
        }
    }

    return controller.wstring() +
           wtools::ConvertToUTF16(fmt::format(" {} {} {}{}", kCmdLineAsDaemon,
                                              kCmdLinePort, port, allowed_ip));
}

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
    auto proc_id = ar.goExecAsDetached(BuildCommandLine(controller_name));
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]", controller_name,
                  proc_id);
        return true;
    }
    XLOG::l("Agent controller '{}' failed to start", controller_name);
    return false;
}

// TODO(sk): make public API and replace all Trailing/trim with this one
void TrimRight(std::string &s, std::string_view chars) {
    auto end = s.find_last_not_of(chars);
    if (end != std::string::npos) {
        s.erase(end + 1);
    }
}

std::string DetermineAgentCtlVersion() {
    auto work_controller = GetWorkController();
    std::error_code ec;
    if (!fs::exists(work_controller, ec)) {
        XLOG::l("There is no controller '{}' ec=[{}]", work_controller,
                ec.value());
        return {};
    }
    auto result = wtools::RunCommand(work_controller.wstring() + L" " +
                                     wtools::ConvertToUTF16(kCmdLineVersion));
    TrimRight(result, "\n\r");
    return result;
}

bool KillAgentController(const fs::path &service) {
    if (cma::IsService()) {
        auto ret = wtools::KillProcess(cfg::files::kAgentCtl, 1);
        // Idiotic loop below mirrors idiotic Windows architecture.
        // MS: Even if process killed, the executable may be for some time busy.
        // And can't be deleted.
        for (int i = 0; i < 20; ++i) {
            if (DeleteControllerInBin(service)) {
                break;
            }
            XLOG::d("error deleting controller");
            std::this_thread::sleep_for(200ms);
        }
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
