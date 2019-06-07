
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/check_mk.h"

#include <chrono>
#include <string>

#include "asio.h"
#include "asio/ip/address_v4.hpp"
#include "asio/ip/address_v6.hpp"
#include "asio/ip/network_v4.hpp"
#include "asio/ip/network_v6.hpp"
#include "cfg.h"
#include "check_mk.h"
#include "onlyfrom.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

// According to requirements from check only_from
// 10.2.3.1  -> 10.2.3.1/32
// 127.0.0.1 -> 0:0:0:0:0:ffff:7f00:1/128
static std::string AddressV4ToCheckMkNetworkV4(std::string_view addr) {
    auto addr_4 = asio::ip::make_address_v4(addr);        //
    auto netw_4 = asio::ip::make_network_v4(addr_4, 32);  // max bits
    return netw_4.to_string();
}

// we want to have WORD Formatted IPV6
// i.e. FFFF:A01:203.
// Based on integration tests from Legacy Windows Agent

// asio::ip::address_v6 -> to hex word represntation
static std::string AddressV6ToHex(asio::ip::address_v6 addr) {
    auto bytes = addr.to_bytes();  // network order raw of bytes

    // bytes to words without changing order:
    const auto raw_words = reinterpret_cast<uint16_t*>(bytes.data());

    // Vectorize to be safe and for the future refactoring
    const std::vector<uint16_t> words{raw_words, raw_words + bytes.size() / 2};

    // conversion, we do not have in C++ easy methods
    std::string hex;
    for (auto w : words) {
        hex += fmt::format("{:x}", ::ntohs(w)) + ":";
    }

    // probably never happens, but keep it have safety with future refactoring
    if (hex.empty()) return {};

    hex.pop_back();  // remove last ":"
    return hex;
}

// "10.2.3.1" -> "0:0:0:0:0:FFFF:A01:203/128"
// requirement from check only_from
static std::string AddressV4ToCheckMkNetworkV6(std::string_view addr) {
    using namespace asio;

    auto addr_4 = ip::make_address_v4(addr);  //
    auto addr_6 = ip::make_address_v6(ip::v4_mapped, addr_4);

    auto hex = AddressV6ToHex(addr_6);

    // bits
    hex += "/128";
    return hex;
}

// function to provide format compatibility for monitoring site
// probably, a bit to pedantic, "aber sicher ist sicher"
std::string AddressToCheckMkString(std::string_view entry) noexcept {
    using namespace cma::cfg;
    using namespace asio;

    // we do not care about network format
    if (of::IsNetwork(entry)) return std::string(entry);

    // normal addresses to be converted in network
    // according to integration tests from LWA
    try {
        if (of::IsAddressV4(entry)) {
            // we need two addresses, ipv4 and compatible ipv6
            auto out = AddressV4ToCheckMkNetworkV4(entry);

            auto hex = AddressV4ToCheckMkNetworkV6(entry);

            if (!hex.empty()) out += " " + hex;
            return out;
        }

        if (of::IsAddressV6(entry)) {
            auto addr = ip::make_address_v6(entry);
            auto hex = AddressV6ToHex(addr);  // again conversion
            hex += "/128";                    // max bits
            return hex;
        }
    } catch (const std::exception& e) {
        XLOG::l("Entry '{}' is bad, exception '{}'", entry, e.what());
    }
    return {};
}

std::string CheckMk::makeBody() {
    using namespace std::chrono;
    using namespace std;
    using namespace cma;
    using namespace wtools;
    using namespace cma::cfg;

    XLOG::t(XLOG_FUNC + " entering");

    pair<string, string> infos[] = {
        // start -----------------------------------------------
        {"Version", CHECK_MK_VERSION},
        {"BuildDate", __DATE__},
        {"AgentOS", "windows"},
        {"Hostname", cfg::GetHostName()},

        {"Architecture", tgt::Is64bit() ? "64bit" : "32bit"},
        {"WorkingDirectory", ConvertToUTF8(cfg::GetWorkingDir())},
        {"ConfigFile", ConvertToUTF8(cfg::GetPathOfRootConfig())},
        {"LocalConfigFile", ConvertToUTF8(cfg::GetPathOfUserConfig())},
        {"AgentDirectory", ConvertToUTF8(cfg::GetRootDir())},
        {"PluginsDirectory", ConvertToUTF8(cfg::GetUserPluginsDir())},
        {"StateDirectory", ConvertToUTF8(cfg::GetStateDir())},
        {"ConfigDirectory", ConvertToUTF8(cfg::GetPluginConfigDir())},
        {"TempDirectory", ConvertToUTF8(cfg::GetTempDir())},
        {"LogDirectory", ConvertToUTF8(cfg::GetLogDir())},
        {"SpoolDirectory", ConvertToUTF8(cfg::GetSpoolDir())},
        {"LocalDirectory", ConvertToUTF8(cfg::GetLocalDir())}
        // end -------------------------------------------------
    };

    std::string out;
    for (const auto& info : infos) {
        out += fmt::format("{}: {}\n", info.first, info.second);
    }

    out += "OnlyFrom:";
    auto only_from = GetInternalArray(groups::kGlobal, vars::kOnlyFrom);
    if (only_from.empty()) {
        return out + " 0.0.0.0/0\n";
    }

    for (auto& entry : only_from) {
        auto value = AddressToCheckMkString(entry);
        if (!value.empty()) out += " " + value;
    }
    out += '\n';
    return out;
}  // namespace provider

}  // namespace provider
};  // namespace cma
