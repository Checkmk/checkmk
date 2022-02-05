// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "onlyfrom.h"

//
#include "asio.h"
//
#include <asio/ip/address_v4.hpp>
#include <asio/ip/address_v6.hpp>
#include <asio/ip/network_v4.hpp>
#include <asio/ip/network_v6.hpp>
#include <string>
#include <string_view>

#include "cfg.h"
#include "logger.h"

namespace cma::cfg::of {

bool IsNetworkV4(std::string_view str) {
    std::error_code ec;
    asio::ip::make_network_v4(str, ec);
    return ec.value() == 0;
}

bool IsNetworkV6(std::string_view str) {
    std::error_code ec;
    asio::ip::make_network_v6(str, ec);
    return ec.value() == 0;
}

bool IsNetwork(std::string_view str) {
    return IsNetworkV4(str) || IsNetworkV6(str);
}

bool IsAddressV4(std::string_view str) {
    std::error_code ec;
    asio::ip::make_address_v4(str, ec);
    return ec.value() == 0;
}

bool IsAddressV6(std::string_view str) {
    std::error_code ec;
    asio::ip::make_address_v6(str, ec);
    return ec.value() == 0;
}
bool IsAddress(std::string_view str) {
    return IsAddressV4(str) || IsAddressV6(str);
}

bool IsIpV6(std::string_view str) {
    return IsAddressV6(str) || IsNetworkV6(str);
}

namespace {
bool IsFromTemplate(std::string_view addr_template, std::string_view address) {
    auto address_t = asio::ip::make_address(addr_template);
    auto address_a = asio::ip::make_address(address);

    if (address_t.is_v6() && address_a.is_v4()) {
        auto address_a_v4 = asio::ip::make_address_v4(address);
        return address_t ==
               asio::ip::make_address_v6(asio::ip::v4_mapped, address_a_v4);
    }

    if (address_t.is_v4() && address_a.is_v6()) {
        return false;
    }
    return address_t == address_a;
}

bool IsFromV4(std::string_view addr_template, std::string_view address) {
    if (!IsAddressV4(address)) return false;  // do not pass

    auto network = asio::ip::make_network_v4(addr_template);
    auto address_a = asio::ip::make_address_v4(address);
    const asio::ip::network_v4 me(address_a, network.prefix_length());
    auto me_can = me.canonical();
    auto net_can = network.canonical();
    return me_can == net_can;
}

bool IsFromV6(std::string_view addr_template, std::string_view address) {
    auto network = asio::ip::make_network_v6(addr_template);
    auto net_can = network.canonical();
    if (IsAddressV6(address)) {
        auto address_a = asio::ip::make_address_v6(address);
        const asio::ip::network_v6 me(address_a, network.prefix_length());
        auto me_can = me.canonical();
        return me_can == net_can;
    }

    auto address_tmp = asio::ip::make_address_v4(address);
    auto address_a =
        asio::ip::make_address_v6(asio::ip::v4_mapped, address_tmp);
    const asio::ip::network_v6 me(address_a, network.prefix_length());
    auto me_can = me.canonical();
    return me_can == net_can;
}
}  // namespace

bool IsValid(std::string_view addr_template, std::string_view address) {
    try {
        if (IsAddress(addr_template)) {
            return IsFromTemplate(addr_template, address);
        }

        if (IsNetworkV4(addr_template)) {
            return IsFromV4(addr_template, address);
        }

        if (IsNetworkV6(addr_template)) {
            return IsFromV6(addr_template, address);
        }

        XLOG::l("Invalid entry '{}' ignored", addr_template);
        return false;

    } catch (const std::exception &e) {
        XLOG::l(
            XLOG_FUNC + " Parameters are invalid '{}' '{}', exception is '{}'",
            addr_template, address, e.what());
        return false;
    }
}
std::string MapToV6Address(std::string_view address) {
    try {
        if (IsAddressV4(address)) {
            auto address_v4 = asio::ip::make_address_v4(address);
            auto address_v6 =
                asio::ip::make_address_v6(asio::ip::v4_mapped, address_v4);
            return address_v6.to_string();
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " Parameter is invalid '{}', exception is '{}'",
                address, e.what());
        return {};
    }
    return {};
}

std::string MapToV6Network(std::string_view network) {
    try {
        if (IsNetworkV4(network)) {
            auto network_v4 = asio::ip::make_network_v4(network);
            auto address_v4 = network_v4.network();
            auto address_v6 =
                asio::ip::make_address_v6(asio::ip::v4_mapped, address_v4);
            auto prefix_len = network_v4.prefix_length() + 128 - 32;
            auto end_network =
                asio::ip::make_network_v6(address_v6, prefix_len);
            return end_network.to_string();
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FUNC + " Parameter is invalid '{}', exception is '{}'",
                network, e.what());
        return {};
    }
    return {};
}

}  // namespace cma::cfg::of
