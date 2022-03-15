
#include "stdafx.h"

#include "agent_controller.h"

#include <versionhelpers.h>

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

namespace {
std::pair<fs::path, fs::path> ServiceName2TargetName(const fs::path &service) {
    return {GetController(service), GetWorkController()};
}

fs::path LegacyPullFile() {
    return fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile;
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

}  // namespace

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

bool IsRunController(const YAML::Node &node) {
    auto controller = cma::yml::GetNode(node, std::string{cfg::groups::kSystem},
                                        std::string{cfg::vars::kController});
    return cfg::GetVal(controller, cfg::vars::kControllerRun, false);
}

bool IsInLegacyMode() {
    std::error_code ec;
    return fs::exists(LegacyPullFile(), ec);
}

fs::path GetController(const fs::path &service) {
    auto controller = service;
    controller.replace_filename(cfg::files::kAgentCtl);
    return controller;
}

fs::path GetWorkController() {
    return fs::path{cfg::GetUserBinDir()} / cfg::files::kAgentCtl;
}

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

    return controller.wstring() + wtools::ConvertToUTF16(fmt::format(
                                      " {} {} {}{} -vv", kCmdLineAsDaemon,
                                      kCmdLinePort, port, allowed_ip));
}

std::optional<uint32_t> StartAgentController(const fs::path &service) {
    XLOG::l.i("starting controller");
    if (!cma::IsService()) {
        return {};
    }

    if (!::IsWindows7OrGreater()) {
        XLOG::l(
            "The agent controller is not compatible with this Windows version. "
            "You can disable using the agent controller by configuring the "
            "Checkmk rule set \"Windows agent controller\" for this host.");
        return false;
    }
    auto controller_name = CopyControllerToBin(service);
    if (controller_name.empty()) {
        XLOG::l("can't copy controller");
        return {};
    }

    wtools::AppRunner ar;
    auto proc_id = ar.goExecAsDetached(BuildCommandLine(controller_name));
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]", controller_name,
                  proc_id);
        return proc_id;
    }
    XLOG::l("Agent controller '{}' failed to start", controller_name);
    return {};
}

// TODO(sk): make public API and replace all Trailing/trim with this one
void TrimRight(std::string &s, std::string_view chars) {
    auto end = s.find_last_not_of(chars);
    if (end != std::string::npos) {
        s.erase(end + 1);
    }
}

namespace {
std::string RunAgentControllerWithParam(std::string_view param) {
    auto work_controller = GetWorkController();
    std::error_code ec;
    if (!fs::exists(work_controller, ec)) {
        XLOG::l("There is no controller '{}' ec=[{}]", work_controller,
                ec.value());
        return {};
    }
    auto result = wtools::RunCommand(work_controller.wstring() + L" " +
                                     wtools::ConvertToUTF16(param));
    TrimRight(result, "\n\r");
    return result;
}
}  // namespace

std::string DetermineAgentCtlVersion() {
    return RunAgentControllerWithParam(kCmdLineVersion);
}

std::string DetermineAgentCtlStatus() {
    return RunAgentControllerWithParam(kCmdLineStatus);
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

namespace {
void CreateLegacyFile() {
    auto file_name = LegacyPullFile();
    std::ofstream ofs(file_name.u8string());
    ofs << "Created by Windows agent";
}
}  // namespace

/// Creates/Deletes file in agent-user dir to satisfy controller requirements
/// marker is used to determine status of the OS
/// marker will be deleted
bool CreateLegacyModeFile(const std::filesystem::path &marker) {
    constexpr auto uninstall_allowed_delay = 10s;
    std::error_code ec;
    if (!fs::exists(marker, ec)) {
        XLOG::l.i("File '{}' absent, assuming fresh install, legacy OFF",
                  marker);
        return false;
    }

    auto timestamp = fs::last_write_time(marker, ec);
    if (ec) {
        XLOG::l.i("File '{}' is strange, assuming bad file, legacy ON", marker);
        CreateLegacyFile();
        return true;
    }

    const auto age = std::chrono::duration_cast<std::chrono::seconds>(
        fs::_File_time_clock::now().time_since_epoch() -
        timestamp.time_since_epoch());
    ON_OUT_OF_SCOPE(fs::remove(marker, ec));
    if (age > uninstall_allowed_delay) {
        XLOG::l.i("File '{}' too old, assuming fresh install, legacy OFF",
                  marker);
        return false;
    }

    auto data = tools::ReadFileInString(marker.wstring().c_str());
    if (!data.has_value()) {
        XLOG::l.i("File '{}' is bad, assuming fresh install, legacy ON",
                  marker);
        return false;
    }

    if ((*data).starts_with(kCmkAgentMarkerNew)) {
        XLOG::l.i("File '{}' from 2.1+, legacy OFF", marker);
        return false;
    }

    CreateLegacyFile();
    XLOG::l.i("File '{}' from 2.0 or earlier, legacy ON", marker);
    return true;
}

}  // namespace cma::ac
