
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/check_mk.h"

#include <chrono>
#include <string>

//
#include "asio.h"
//
#include <asio/ip/address_v4.hpp>
#include <asio/ip/address_v6.hpp>
#include <asio/ip/network_v4.hpp>
#include <asio/ip/network_v6.hpp>

#include "cfg.h"
#include "check_mk.h"
#include "common/version.h"
#include "onlyfrom.h"

namespace cma::provider {

// function to provide format compatibility for monitoring site
// probably, a bit to pedantic
std::string AddressToCheckMkString(std::string_view entry) {
    if (cfg::of::IsNetwork(entry)) return std::string{entry};

    try {
        if (cfg::of::IsAddressV4(entry)) {
            return std::string{entry};
        }

        if (cfg::of::IsAddressV6(entry)) {
            return std::string{entry};
        }
    } catch (const std::exception& e) {
        XLOG::l("Entry '{}' is bad, exception '{}'", entry, e.what());
    }

    XLOG::l("Entry '{}' is bad, we return nothing", entry);
    return {};
}

std::string CheckMk::makeOnlyFrom() {
    auto only_from =
        cfg::GetInternalArray(cfg::groups::kGlobal, cfg::vars::kOnlyFrom);
    if (only_from.empty()) return {};
    if (only_from.size() == 1 && only_from[0] == "~") return {};

    std::string out;
    for (auto& entry : only_from) {
        auto value = AddressToCheckMkString(entry);
        if (!value.empty()) out += value + " ";
    }

    if (!out.empty()) out.pop_back();  // last space

    return out;
}

namespace {
std::string MakeInfo() {
    const std::pair<std::string, std::string> infos[] = {
        {"Version", CHECK_MK_VERSION},
        {"BuildDate", __DATE__},
        {"AgentOS", "windows"},
        {"Hostname", cfg::GetHostName()},
        {"Architecture", tgt::Is64bit() ? "64bit" : "32bit"},
    };
    std::string out;
    for (const auto& info : infos) {
        out += fmt::format("{}: {}\n", info.first, info.second);
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
    for (const auto& d : directories) {
        out +=
            fmt::format("{}: {}\n", d.first, wtools::ConvertToUTF8(d.second));
    }

    return out;
}

}  // namespace

std::string CheckMk::makeBody() {
    using namespace std::string_literals;

    auto out = MakeInfo();
    out += MakeDirs();
    out += "OnlyFrom: "s + makeOnlyFrom() + "\n"s;

    return out;
}

};  // namespace cma::provider
