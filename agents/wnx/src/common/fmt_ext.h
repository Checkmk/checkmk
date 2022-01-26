// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// support ftomatting of user definde data types
// No C++ file
#pragma once

#include <fmt/format.h>

#include <chrono>
#include <filesystem>

template <>
struct fmt::formatter<std::filesystem::path> {
    constexpr auto parse(format_parse_context &ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::filesystem::path &p, FormatContext &ctx) {
        return format_to(ctx.out(), "{}", p.u8string());
    }
};

template <>
struct fmt::formatter<std::chrono::milliseconds> {
    constexpr auto parse(format_parse_context &ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::chrono::milliseconds &p, FormatContext &ctx) {
        return format_to(ctx.out(), "{}ms", p.count());
    }
};

template <>
struct fmt::formatter<std::chrono::seconds> {
    constexpr auto parse(format_parse_context &ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::chrono::seconds &p, FormatContext &ctx) {
        return format_to(ctx.out(), "{}s", p.count());
    }
};

template <>
struct fmt::formatter<std::chrono::microseconds> {
    constexpr auto parse(format_parse_context &ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::chrono::microseconds &p, FormatContext &ctx) {
        return format_to(ctx.out(), "{}us", p.count());
    }
};

template <>
struct fmt::formatter<std::chrono::nanoseconds> {
    constexpr auto parse(format_parse_context &ctx) {
        // Return an iterator past the end of the parsed range:
        return ctx.end();
    }

    template <typename FormatContext>
    auto format(const std::chrono::nanoseconds &p, FormatContext &ctx) {
        return format_to(ctx.out(), "{}ns", p.count());
    }
};
