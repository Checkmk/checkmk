#include "types.h"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <string>
#include "Environment.h"
#include "PerfCounterCommon.h"
#include "stringutil.h"

template <>
bool from_string<bool>(const WinApiAdaptor &, const std::string &value) {
    return parse_boolean(value.c_str());
}

template <>
int from_string<int>(const WinApiAdaptor &, const std::string &value) {
    return std::stol(value);
}

template <>
std::string from_string<std::string>(const WinApiAdaptor &,
                                     const std::string &value) {
    return value;
}

template <>
ipspec *from_string<ipspec *>(const WinApiAdaptor &winapi,
                              const std::string &value) {
    ipspec *result = new ipspec();

    char *slash_pos = strchr(value.c_str(), '/');
    if (slash_pos != NULL) {
        // ipv4/ipv6 agnostic
        result->bits = strtol(slash_pos + 1, NULL, 10);
    } else {
        result->bits = 0;
    }

    result->ipv6 = strchr(value.c_str(), ':') != NULL;

    if (result->ipv6) {
        if (result->bits == 0) {
            result->bits = 128;
        }
        stringToIPv6(value.c_str(), result->ip.v6.address, winapi);
        netmaskFromPrefixIPv6(result->bits, result->ip.v6.netmask, winapi);

        // TODO verify that host part is 0
    } else {
        if (result->bits == 0) {
            result->bits = 32;
        }

        stringToIPv4(value.c_str(), result->ip.v4.address);
        netmaskFromPrefixIPv4(result->bits, result->ip.v4.netmask);

        if ((result->ip.v4.address & result->ip.v4.netmask) !=
            result->ip.v4.address) {
            fprintf(stderr, "Invalid only_hosts entry: host part not 0: %s",
                    value.c_str());
            exit(1);
        }
    }
    return result;
}

template <>
mrpe_entry *from_string<mrpe_entry *>(const WinApiAdaptor &winapi,
                                      const std::string &value) {
    mrpe_entry *result = new mrpe_entry();
    memset(result, 0, sizeof(mrpe_entry));

    std::string service_description;
    std::string command_line;

    {
        std::stringstream str(value);
        getline(str, service_description, ' ');
        getline(str, command_line);
    }

    // Strip any " from start and end
    if (!command_line.empty() && command_line.front() == '"') {
        command_line = command_line.substr(1);
    }
    if (!command_line.empty() && command_line.back() == '"') {
        command_line = command_line.substr(0, command_line.length() - 1);
    }

    if (command_line.empty()) {
        delete result;
        throw StringConversionError(
            "Invalid command specification for mrpe:\r\n"
            "Format: SERVICEDESC COMMANDLINE");
    }

    if (winapi.PathIsRelative(command_line.c_str())) {
        Environment *env = Environment::instance();
        if (env == nullptr) {
            delete result;
            throw StringConversionError("No environment");
        }
        snprintf(result->command_line, sizeof(result->command_line), "%s\\%s",
                 env->agentDirectory().c_str(), lstrip(command_line.c_str()));
    } else {
        strncpy(result->command_line, command_line.c_str(),
                sizeof(result->command_line));
    }

    strncpy(result->service_description, service_description.c_str(),
            sizeof(result->service_description));

    // compute plugin name, drop directory part
    std::string plugin_name;
    {
        std::stringstream str(command_line);
        getline(str, plugin_name, ' ');
        plugin_name = std::string(
            plugin_name.begin() + plugin_name.find_last_of("/\\") + 1,
            plugin_name.end());
    }
    strncpy(result->plugin_name, plugin_name.c_str(),
            sizeof(result->plugin_name));
    return result;
}

template <>
winperf_counter *from_string<winperf_counter *>(const WinApiAdaptor &winapi,
                                                const std::string &value) {
    size_t colonIdx = value.find_last_of(":");
    if (colonIdx == std::string::npos) {
        fprintf(stderr,
                "Invalid counter '%s' in section [winperf]: need number(or "
                "text) and colon, e.g. 238:processor.\n",
                value.c_str());
        exit(1);
    }
    winperf_counter *result = new winperf_counter();
    result->name = std::string(value.begin() + colonIdx + 1, value.end());

    std::string base_id(value.begin(), value.begin() + colonIdx);

    auto non_digit = std::find_if_not(base_id.begin(), base_id.end(), isdigit);

    if (non_digit == base_id.end()) {
        result->id = std::stoi(base_id);
    } else {
        result->id = resolveCounterName(winapi, base_id);
        if (result->id == -1) {
            delete result;
            throw StringConversionError(
                "No matching performance counter id found for " + value);
        }
    }

    return result;
}

template <>
script_execution_mode from_string<script_execution_mode>(
    const WinApiAdaptor &, const std::string &value) {
    if (value == "async")
        return ASYNC;
    else if (value == "sync")
        return SYNC;
    throw std::runtime_error("invalid execution mode");
}

template <>
script_async_execution from_string<script_async_execution>(
    const WinApiAdaptor &, const std::string &value) {
    if (value == "parallel")
        return PARALLEL;
    else if (value == "sequential")
        return SEQUENTIAL;
    throw std::runtime_error("invalid async mode");
}

template <>
eventlog_config_entry from_string<eventlog_config_entry>(
    const WinApiAdaptor &, const std::string &value) {
    // this parses only what's on the right side of the = in the configuration
    // file
    std::stringstream str(value);

    bool hide_context = false;
    int level = 0;

    std::string entry;
    while (std::getline(str, entry, ' ')) {
        if (entry == "nocontext")
            hide_context = 1;
        else if (entry == "off")
            level = -1;
        else if (entry == "all")
            level = 0;
        else if (entry == "warn")
            level = 1;
        else if (entry == "crit")
            level = 2;
        else {
            fprintf(stderr,
                    "Invalid log level '%s'.\r\n"
                    "Allowed are off, all, warn and crit.\r\n",
                    entry.c_str());
        }
    }

    return eventlog_config_entry(level, hide_context ? 1 : 0, "", false);
}

static const char *level_name(int level_id) {
    switch (level_id) {
        case -1:
            return "off";
        case 0:
            return "all";
        case 1:
            return "warn";
        case 2:
            return "crit";
        default:
            return "invalid";
    }
}

std::ostream &operator<<(std::ostream &out, const eventlog_config_entry &val) {
    out << val.name << " = ";
    if (val.hide_context) {
        out << "nocontext ";
    }
    out << level_name(val.level);
    return out;
}
