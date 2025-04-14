// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/check_mk.h"

#include <string>
#include <cerrno>

//
#include "wnx/asio.h"
//

#include "common/version.h"
#include "wnx/agent_controller.h"
#include "wnx/cfg.h"
#include "wnx/install_api.h"
#include "wnx/onlyfrom.h"

using namespace std::string_literals;

namespace cma::provider {

// tested manually changing time
std::string GetTimezoneOffset(
    std::chrono::time_point<std::chrono::system_clock> tp) {
    const auto tm = std::chrono::system_clock::to_time_t(tp);
    const auto ret = std::put_time(std::localtime(&tm), "%z");
    std::stringstream sss;
    sss << ret;
    return sss.str();
}

// function to provide format compatibility for monitoring site
// probably, a bit to pedantic
std::string AddressToCheckMkString(std::string_view entry) {
    if (cfg::of::IsNetwork(entry)) {
        return std::string{entry};
    }

    try {
        if (cfg::of::IsAddressV4(entry) || cfg::of::IsAddressV6(entry)) {
            return std::string{entry};
        }
    } catch (const std::exception &e) {
        XLOG::l("Entry '{}' is bad, exception '{}'", entry, e);
    }

    XLOG::l("Entry '{}' is bad, we return nothing", entry);
    return {};
}

std::string CheckMk::makeOnlyFrom() {
    const auto only_from =
        cfg::GetInternalArray(cfg::groups::kGlobal, cfg::vars::kOnlyFrom);
    if (only_from.empty() || only_from.size() == 1 && only_from[0] == "~") {
        return {};
    }

    std::string out;
    for (auto &entry : only_from) {
        auto value = AddressToCheckMkString(entry);
        if (!value.empty()) {
            out += value + " ";
        }
    }

    if (!out.empty()) {
        out.pop_back();  // last space
    }

    return out;
}

namespace {
std::string MakeInfo() {
    const auto os = wtools::GetOsInfo();
    const std::pair<std::string, std::optional<std::string>> infos[] = {
        {"Version", {CHECK_MK_VERSION}},
        {"BuildDate", {__DATE__}},
        {"AgentOS", {"windows"}},
        {"Hostname", {cfg::GetHostName()}},
        {"Architecture", {tgt::Is64bit() ? "64bit" : "32bit"}},
        {"OSName", os.has_value() ? std::optional{wtools::ToUtf8(os->name)}
                                  : std::nullopt},
        {"OSVersion", os.has_value()
                          ? std::optional{wtools::ToUtf8(os->version)}
                          : std::nullopt},
        {"OSType", {"windows"}},
        {"Time", {PrintIsoTime(std::chrono::system_clock::now())}},
    };
    std::string out;
    for (const auto &info : infos) {
        if (info.second.has_value()) {
            out += fmt::format("{}: {}\n", info.first, info.second.value());
        } else {
            XLOG::l("Info '{}' is empty", info.first);
        }
    }

    return out;
}
std::string MakeDirs() {
    const std::pair<std::string, std::wstring> directories[] = {
        {"WorkingDirectory", cfg::GetWorkingDir()},
        {"ConfigFile", cfg::GetPathOfRootConfig()},
        {"LocalConfigFile", cfg::GetPathOfUserConfig()},
        {"AgentDirectory", cfg::GetRootDir()},
        {"PluginsDirectory", cfg::GetUserPluginsDir()},
        {"StateDirectory", cfg::GetStateDir()},
        {"ConfigDirectory", cfg::GetPluginConfigDir()},
        {"TempDirectory", cfg::GetTempDir()},
        {"LogDirectory", cfg::GetLogDir()},
        {"SpoolDirectory", cfg::GetSpoolDir()},
        {"LocalDirectory", cfg::GetLocalDir()}};

    std::string out;
    for (const auto &d : directories) {
        out += fmt::format("{}: {}\n", d.first, wtools::ToUtf8(d.second));
    }

    return out;
}

std::tm ToLocalTime(std::chrono::time_point<std::chrono::system_clock> now) {
    const std::time_t now_c = std::chrono::system_clock::to_time_t(now);
    std::tm local_time{};
    errno = 0;
    if (localtime_s(&local_time, &now_c) != 0) {
        XLOG::d.e("ToLocalTime: localtime_s failed with errno {}", errno);
    }
    return local_time;
}

}  // namespace

std::string PrintIsoTime(
    std::chrono::time_point<std::chrono::system_clock> now) {
    auto lt = ToLocalTime(now);
    return fmt::format("{:4}-{:02}-{:02}T{:02}:{:02}:{:02}{}",
                       lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour,
                       lt.tm_min, lt.tm_sec, GetTimezoneOffset(now));
}

std::string CheckMk::makeBody() {
    auto out = MakeInfo();
    out += MakeDirs();
    out += "OnlyFrom: "s + makeOnlyFrom() + "\n"s;
    out += section::MakeHeader(section::kCheckMkCtlStatus);

    if (const auto json = ac::DetermineAgentCtlStatus(); !json.empty()) {
        out += json + "\n";
    }

    if (auto install_api_err = install::api_err::Get()) {
        out += "<<<check_mk>>>\n";
        out += fmt::format("UpdateFailed: The last agent update failed. {}\n",
                           wtools::ToUtf8(*install_api_err));
        out += "UpdateRecoverAction: Contact with system administrator.\n";
    } else if (install::GetLastMsiFailReason()) {
        out += "<<<check_mk>>>\n";
        out +=
            "UpdateFailed: The last agent update failed. Supplied Python environment is not compatible with OS. \n";
        out +=
            "UpdateRecoverAction: Please change the rule 'Setup Python environment' to 'legacy' in setup.\n";
    }

    return out;
}

}  // namespace cma::provider
