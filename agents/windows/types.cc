#include "types.h"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <string>
#include "Environment.h"
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
