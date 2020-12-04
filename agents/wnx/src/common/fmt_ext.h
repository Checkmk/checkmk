// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//
// support ftomatting of user definde data types
// No C++ file
#pragma once

#include <filesystem>
#include <fmt/format.h>

template <>
struct fmt::formatter<std::filesystem::path> {
    constexpr auto parse(format_parse_context& ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::filesystem::path& p, FormatContext& ctx) {
        return format_to(ctx.out(), "{}", p.u8string());
    }
};
