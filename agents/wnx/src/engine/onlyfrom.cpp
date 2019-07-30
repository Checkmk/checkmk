// Windows Tools
#include "stdafx.h"

#include "onlyfrom.h"

#include <string>
#include <string_view>

#include "asio.h"
#include "asio/ip/address_v4.hpp"
#include "asio/ip/address_v6.hpp"
#include "asio/ip/network_v4.hpp"
#include "asio/ip/network_v6.hpp"
#include "cfg.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma::cfg::of {

bool IsNetworkV4(std::string_view Str) {
    std::error_code ec;
    asio::ip::make_network_v4(Str, ec);
    return ec.value() == 0;
}

bool IsNetworkV6(std::string_view Str) {
    std::error_code ec;
    asio::ip::make_network_v6(Str, ec);
    return ec.value() == 0;
}

bool IsNetwork(std::string_view Str) {
    return IsNetworkV4(Str) || IsNetworkV6(Str);
}

bool IsAddressV4(std::string_view Str) {
    std::error_code ec;
    asio::ip::make_address_v4(Str, ec);
    return ec.value() == 0;
}

bool IsAddressV6(std::string_view Str) {
    std::error_code ec;
    asio::ip::make_address_v6(Str, ec);
    return ec.value() == 0;
}
bool IsAddress(std::string_view Str) {
    return IsAddressV4(Str) || IsAddressV6(Str);
}

bool IsIpV6(std::string_view Str) {
    return IsAddressV6(Str) || IsNetworkV6(Str);
}

bool IsValid(std::string_view Template, std::string_view Address) {
    try {
        if (IsAddress(Template)) {
            auto address_t = asio::ip::make_address(Template);
            auto address_a = asio::ip::make_address(Address);

            if (address_t.is_v6() && address_a.is_v4()) {
                auto address_a_v4 = asio::ip::make_address_v4(Address);
                return address_t == asio::ip::make_address_v6(
                                        asio::ip::v4_mapped, address_a_v4);
            }

            if (address_t.is_v4() && address_a.is_v6()) {
                return false;
            }
            return address_t == address_a;
        } else if (IsNetworkV4(Template)) {
            if (!IsAddressV4(Address)) return false;  // do not pass

            auto network = asio::ip::make_network_v4(Template);
            auto address_a = asio::ip::make_address_v4(Address);
            const asio::ip::network_v4 me(address_a, network.prefix_length());
            auto me_can = me.canonical();
            auto net_can = network.canonical();
            return me_can == net_can;
        } else if (IsNetworkV6(Template)) {
            auto network = asio::ip::make_network_v6(Template);
            auto net_can = network.canonical();
            if (IsAddressV6(Address)) {
                auto address_a = asio::ip::make_address_v6(Address);
                const asio::ip::network_v6 me(address_a,
                                              network.prefix_length());
                auto me_can = me.canonical();
                return me_can == net_can;
            } else {
                auto address_tmp = asio::ip::make_address_v4(Address);
                auto address_a =
                    asio::ip::make_address_v6(asio::ip::v4_mapped, address_tmp);
                const asio::ip::network_v6 me(address_a,
                                              network.prefix_length());
                auto me_can = me.canonical();
                return me_can == net_can;
            }
        } else {
            XLOG::l("Invalid entry {} ignored", Template);
            return false;
        }
    } catch (const std::exception& e) {
        XLOG::l(
            XLOG_FUNC + " Parameters are invalid '{}' '{}', exception is '{}'",
            Template, Address, e.what());
        return false;
    }
}
std::string MapToV6Address(std::string_view Address) {
    try {
        if (IsAddressV4(Address)) {
            auto address_v4 = asio::ip::make_address_v4(Address);
            auto address_v6 =
                asio::ip::make_address_v6(asio::ip::v4_mapped, address_v4);
            return address_v6.to_string();
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " Parameter is invalid '{}', exception is '{}'",
                Address, e.what());
        return {};
    }
    return {};
}

std::string MapToV6Network(std::string_view Network) {
    try {
        if (IsNetworkV4(Network)) {
            auto network_v4 = asio::ip::make_network_v4(Network);
            auto address_v4 = network_v4.network();
            auto address_v6 =
                asio::ip::make_address_v6(asio::ip::v4_mapped, address_v4);
            auto prefix_len = network_v4.prefix_length() + 128 - 32;
            auto end_network =
                asio::ip::make_network_v6(address_v6, prefix_len);
            return end_network.to_string();
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FUNC + " Parameter is invalid '{}', exception is '{}'",
                Network, e.what());
        return {};
    }
    return {};
}

}  // namespace cma::cfg::of
