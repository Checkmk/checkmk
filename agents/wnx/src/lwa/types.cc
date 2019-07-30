#include "stdafx.h"

#include "types.h"

#include <algorithm>
#include <cstring>
#include <sstream>
#include <string>

#include "cfg.h"
#include "logger.h"
#include "stringutil.h"
namespace fs = std::experimental::filesystem;

template <>
bool from_string<bool>(const std::string &value) {
    return parse_boolean(value.c_str());
}

template <>
int from_string<int>(const std::string &value) {
    return std::stol(value);
}

template <>
std::string from_string<std::string>(const std::string &value) {
    return value;
}

template <>
fs::path from_string<fs::path>(const std::string &value) {
    return {value};
}

template <>
ipspec from_string<ipspec>(const std::string &value) {
    ipspec result;

    auto slash_pos = strchr(value.c_str(), '/');
    if (slash_pos != NULL) {
        // ipv4/ipv6 agnostic
        result.bits = strtol(slash_pos + 1, NULL, 10);
    } else {
        result.bits = 0;
    }

    result.ipv6 = strchr(value.c_str(), ':') != NULL;

    if (result.ipv6) {
        if (result.bits == 0) {
            result.bits = 128;
        }
        stringToIPv6(value.c_str(), result.ip.v6.address);
        netmaskFromPrefixIPv6(result.bits, result.ip.v6.netmask);

        // TODO verify that host part is 0
    } else {
        if (result.bits == 0) {
            result.bits = 32;
        }

        stringToIPv4(value.c_str(), result.ip.v4.address);
        netmaskFromPrefixIPv4(result.bits, result.ip.v4.netmask);

        if ((result.ip.v4.address & result.ip.v4.netmask) !=
            result.ip.v4.address) {
            std::cerr << "Invalid only_hosts entry: host part not 0: " << value
                      << std::endl;
            exit(1);
        }
    }
    return result;
}

std::ostream &operator<<(std::ostream &os, const ipspec &ips) {
    if (ips.ipv6) {
        std::array<uint16_t, 8> hostByteAddress = {0};
        std::transform(
            ips.ip.v6.address, ips.ip.v6.address + 8, hostByteAddress.begin(),
            [&ips](const uint16_t netshort) { return ::ntohs(netshort); });
        os << join(hostByteAddress.cbegin(), hostByteAddress.cend(), ":",
                   std::ios::hex)
           << "/" << ips.bits;
    } else {
        os << (ips.ip.v4.address & 0xff) << "."
           << (ips.ip.v4.address >> 8 & 0xff) << "."
           << (ips.ip.v4.address >> 16 & 0xff) << "."
           << (ips.ip.v4.address >> 24 & 0xff) << "/" << ips.bits;
    }

    return os;
}

ipspec toIPv6(const ipspec &ips) {
    ipspec result;
    // first 96 bits are fixed: 0:0:0:0:0:ffff
    result.bits = 96 + ips.bits;
    result.ipv6 = true;

    uint32_t ipv4_loopback = 0;
    stringToIPv4("127.0.0.1", ipv4_loopback);

    // For IPv4 loopback address 127.0.0.1, add corresponding IPv6
    // loopback address 0:0:0:0:0:0:0:1 (also known as ::1).
    if (ips.ip.v4.address == ipv4_loopback) {
        memset(result.ip.v6.address, 0, sizeof(uint16_t) * 7);
        result.ip.v6.address[7] = ::htons(0x1);
    } else {
        memset(result.ip.v6.address, 0, sizeof(uint16_t) * 5);
        result.ip.v6.address[5] = 0xFFFFu;
        result.ip.v6.address[6] =
            static_cast<uint16_t>(ips.ip.v4.address & 0xFFFFu);
        result.ip.v6.address[7] =
            static_cast<uint16_t>(ips.ip.v4.address >> 16);
    }

    netmaskFromPrefixIPv6(result.bits, result.ip.v6.netmask);

    return result;
}

template <>
winperf_counter from_string<winperf_counter>(const std::string &value) {
    using namespace wtools;

    size_t colonIdx = value.find_last_of(":");
    if (colonIdx == std::string::npos) {
        XLOG::l() << "Invalid counter '" << value
                  << "' in section [winperf]: need number(or "
                     "text) and colon, e.g. 238:processor.";
        return {0, "", ""};
    }

    std::string name(value.begin() + colonIdx + 1, value.end());
    std::string base_id(value.begin(), value.begin() + colonIdx);
    auto non_digit = std::find_if_not(base_id.begin(), base_id.end(), isdigit);

    if (non_digit == base_id.end()) return {std::stoi(base_id), name, base_id};

    auto x =
        wtools::perf::FindPerfIndexInRegistry(wtools::ConvertToUTF16(base_id));
    if (x.has_value()) return {(int)x.value(), name, base_id};

    return {0, "", ""};
}

// Add a new globline from the config file:
// C:/Testfile | D:/var/log/data.log D:/tmp/art*.log
// This globline is split into tokens which are processed by
// process_glob_expression
template <>
globline_container from_string<globline_container>(const std::string &value) {
    // Each globline receives its own pattern container
    // In case new files matching the glob pattern are we
    // we already have all state,regex patterns available
    glob_tokens_t tokens;

    // Split globline into tokens
    std::regex split_exp("[^|]+");
    std::string copy(value);
    std::regex_token_iterator<std::string::iterator> iter(
        copy.begin(), copy.end(), split_exp),
        end;

    for (; iter != end; ++iter) {
        std::string descriptor = iter->str();
        ltrim(descriptor);
        glob_token new_token;

        for (const auto &token :
             std::vector<std::string>{"nocontext", "from_start", "rotated"}) {
            std::regex tokenRegex("\\b" + token + "\\b");
            if (std::regex_search(descriptor, tokenRegex)) {
                if (token == "nocontext") {
                    new_token.nocontext = true;
                } else if (token == "from_start") {
                    new_token.from_start = true;
                } else if (token == "rotated") {
                    new_token.rotated = true;
                }
                descriptor = std::regex_replace(descriptor, tokenRegex, "");
                ltrim(descriptor);
            }
        }

        new_token.pattern = descriptor;
        tokens.push_back(new_token);
    }

    return {tokens, {}};
}

enum class QuoteType { none, singleQuoted, doubleQuoted };

inline bool quoted(QuoteType qt) { return qt != QuoteType::none; }

inline QuoteType getQuoteType(const std::string &s) {
    if (s.front() == '\'' && s.back() == '\'') {
        return QuoteType::singleQuoted;
    } else if (s.front() == '"' && s.back() == '"') {
        return QuoteType::doubleQuoted;
    } else {
        return QuoteType::none;
    }
}

void removeQuotes(std::string &s, QuoteType qt) {
    if (quoted(qt)) {
        s = s.substr(1, s.size() - 2);
    }
}

void wrapInQuotes(std::string &s, QuoteType qt) {
    if (quoted(qt)) {
        char quote = (qt == QuoteType::singleQuoted) ? '\'' : '"';
        s.reserve(s.size() + 2);
        s.insert(0, 1, quote);
        s.push_back(quote);
    }
}

void normalizeCommand(std::string &cmd) {
    if (isPathRelative(cmd)) {
        ltrim(cmd);
        rtrim(cmd);
        auto quoteType = getQuoteType(cmd);
        removeQuotes(cmd, quoteType);
        auto dir = cma::cfg::GetUserDir();
        cmd.insert(0, wtools::ConvertToUTF8(dir) + "\\");
        wrapInQuotes(cmd, quoteType);
    }
}

template <>
mrpe_entry from_string<mrpe_entry>(const std::string &value) {
    std::vector<std::string> tokens = tokenizePossiblyQuoted(value);

    if (tokens.size() < 2) {
        throw StringConversionError(
            "Invalid command specification for mrpe:\r\n"
            "Format: SERVICEDESC COMMANDLINE");
    }

    auto plugin_name = tokens[1];  // Intentional copy
    // compute plugin name, drop directory part
    removeQuotes(plugin_name, getQuoteType(plugin_name));

    for (const auto &delimiter : {"/", "\\"}) {
        auto pos = plugin_name.find_last_of(delimiter);
        if (pos != std::string::npos) {
            plugin_name = plugin_name.substr(pos + 1);
            break;
        }
    }

    std::string command_line =
        join(std::next(tokens.cbegin(), 2), tokens.cend(), " ");
    auto &cmd = tokens[1];
    normalizeCommand(cmd);

    if (command_line.empty()) {
        command_line = cmd;
    } else {
        command_line.insert(0, cmd + " ");
    }

    auto &service_description = tokens[0];
    removeQuotes(service_description, getQuoteType(service_description));

    return {"", command_line, plugin_name, service_description};
}

template <>
std::string ToYamlString(const winperf_counter &WinPerfCounter, bool) {
    std::string out = "- ";

    out += WinPerfCounter.base_id + ": ";
    out += WinPerfCounter.name + "\n";

    return out;
}

template <>
std::string ToYamlString(const mrpe_entry &Entry, bool) {
    namespace fs = std::filesystem;

    std::string out = "- check = ";
    std::string p = Entry.command_line;
    auto data_path = wtools::ConvertToUTF8(cma::cfg::GetUserDir());
    auto pos = p.find(data_path);
    if (pos == 0 || pos == 1) {
        cma::cfg::ReplaceInString(p, data_path,
                                  cma::cfg::vars::kProgramDataFolder);
    }

    out += Entry.service_description;
    out += " ";
    out += p;

    return out;
}
