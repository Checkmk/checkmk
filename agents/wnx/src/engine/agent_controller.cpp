
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
using namespace std::string_literals;

namespace cma::ac {

fs::path LegacyPullFile() {
    return fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile;
}

fs::path ControllerFlagFile() {
    return fs::path{cfg::GetUserDir()} / ac::kControllerFlagFile;
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

template <typename T>
int ToInt(const T value) noexcept {
    try {
        return std::stoi(value);
    } catch (const std::exception & /*exc*/) {
        return -1;
    }
}

YAML::Node GetControllerNode() {
    return yml::GetNode(cfg::GetLoadedConfig(),
                        std::string{cfg::groups::kSystem},
                        std::string{cfg::vars::kController});
}

uint16_t GetPortFromString(const std::string &str) {
    auto table = tools::SplitString(str, ":");
    if (table.size() != 2) {
        return 0;
    }

    auto port = ToInt(table[1]);
    return port < 1000 ? 0 : port;
}

std::string GetConfiguredAgentChannel() {
    auto controller_config = GetControllerNode();
    auto result =
        cfg::GetVal(controller_config, cfg::vars::kControllerAgentChannel,
                    std::string{cfg::defaults::kControllerAgentChannelDefault});
    auto port = GetPortFromString(result);
    if (port == 0) {
        XLOG::l("Invalid configured agent channel '{}' use default", result);
        return std::string{cfg::defaults::kControllerAgentChannelDefault};
    }

    return result;
}
bool GetConfiguredForceLegacy() {
    auto controller_config = GetControllerNode();
    return cfg::GetVal(controller_config, cfg::vars::kControllerForceLegacy,
                       cfg::defaults::kControllerForceLegacy);
}

}  // namespace

uint16_t GetConfiguredAgentChannelPort() {
    return GetPortFromString(GetConfiguredAgentChannel());
}

bool GetConfiguredLocalOnly() {
    auto controller_config = GetControllerNode();
    return cfg::GetVal(controller_config, cfg::vars::kControllerLocalOnly,
                       cfg::defaults::kControllerLocalOnly);
}

bool GetConfiguredCheck() {
    auto controller_config = GetControllerNode();
    return cfg::GetVal(controller_config, cfg::vars::kControllerCheck,
                       cfg::defaults::kControllerCheck);
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
    auto agent_channel = GetConfiguredAgentChannel();
    std::string allowed_ip;
    if (!only_from.empty()) {
        allowed_ip = " "s + std::string{kCmdLineAllowedIp};
        for (const auto &a : only_from) {
            allowed_ip += " " + a;
        }
    }

    return controller.wstring() +
           wtools::ConvertToUTF16(fmt::format(" {} {} {} {} {}{} -vv",  //
                                              kCmdLineAsDaemon,    // daemon
                                              kCmdLinePort, port,  // -P 6556
                                              kCmdLineChannel,
                                              agent_channel,  // --channel 50001
                                              allowed_ip));   // -A ip ip ip ip
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
    const auto cmdline = BuildCommandLine(controller_name);
    auto proc_id = ar.goExecAsDetached(cmdline);
    if (proc_id != 0) {
        XLOG::l.i("Agent controller '{}' started pid [{}]",
                  wtools::ToUtf8(cmdline), proc_id);
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
const std::string legacy_pull_text{"File '{}'  {}, legacy pull mode {}"};

bool ConditionallyCreateLegacyFile(const fs::path &marker,
                                   std::string_view message) {
    bool created{false};
    if (!ac::IsControllerFlagFileExists()) {
        CreateLegacyFile();
        created = true;
    }
    XLOG::l.i(legacy_pull_text, marker, message, created ? "ON" : "OFF");

    return created;
}
}  // namespace

/// Creates file in agent-user dir to satisfy controller requirements
/// marker is used to determine status of the OS
/// marker will be deleted
bool CreateLegacyModeFile(const fs::path &marker) {
    constexpr auto uninstall_allowed_delay = 10s;
    std::error_code ec;
    if (!fs::exists(marker, ec)) {
        return ConditionallyCreateLegacyFile(
            marker, "is absent, assuming fresh install");
    }

    auto timestamp = fs::last_write_time(marker, ec);
    if (ec) {
        return ConditionallyCreateLegacyFile(marker,
                                             "is strange, assuming bad file");
    }

    const auto age = std::chrono::duration_cast<std::chrono::seconds>(
        fs::_File_time_clock::now().time_since_epoch() -
        timestamp.time_since_epoch());
    if (age > uninstall_allowed_delay) {
        return ConditionallyCreateLegacyFile(
            marker, "is too old, assuming fresh install");
    }

    auto data = tools::ReadFileInString(marker.wstring().c_str());
    if (!data.has_value()) {
        return ConditionallyCreateLegacyFile(marker,
                                             "is bad, assuming fresh install");
    }

    bool reinstall_new = (*data).starts_with(kCmkAgentMarkerNew);
    if (reinstall_new) {
        XLOG::l.i("File '{}' is from 2.1+ legacy pull mode  N/A", marker);
        return false;
    }
    return ConditionallyCreateLegacyFile(marker, "is from 2.0 or earlier");
}

void CreateControllerFlagFile() {
    auto file_name = ControllerFlagFile();
    std::ofstream ofs(file_name.u8string());
    ofs << "Created by Windows agent";
}

bool IsControllerFlagFileExists() {
    std::error_code ec;
    return fs::exists(ControllerFlagFile(), ec);
}

void CreateArtifacts(const fs::path &marker, bool controller_exists) {
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(marker, ec));
    if (!controller_exists) {
        return;
    }
    if (GetConfiguredForceLegacy()) {
        XLOG::l.i(legacy_pull_text, marker,
                  " is ignored, configured to always create file", "ON");
        CreateLegacyFile();
    } else if (!IsControllerFlagFileExists()) {
        CreateLegacyModeFile(marker);
    }
    CreateControllerFlagFile();
}

}  // namespace cma::ac
