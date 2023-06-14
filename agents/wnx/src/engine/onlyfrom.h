// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ONLYFROM_H
#define ONLYFROM_H

#include <string>
#include <string_view>

namespace cma::cfg::of {

// wrappers to correctly analyze ip addresses
// we need quite limited functionality, so get it
// we are not going to use manually crafted ip address parsers
// ergo we get everything from the asio

bool IsNetworkV4(std::string_view str);
bool IsNetworkV6(std::string_view str);
bool IsNetwork(std::string_view str);

bool IsAddressV4(std::string_view str);
bool IsAddressV6(std::string_view str);
bool IsAddress(std::string_view str);
bool IsIpV6(std::string_view str);

bool IsValid(std::string_view addr_template, std::string_view address);
std::string MapToV6Address(std::string_view address);
std::string MapToV6Network(std::string_view network);

}  // namespace cma::cfg::of

#endif  // ONLYFROM_H
