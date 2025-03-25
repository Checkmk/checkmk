// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef CHECK_MK_H
#define CHECK_MK_H

#include <chrono>
#include <string>
#include <string_view>

#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

/// Converts address entry from config file into
///
/// Expected by check_mk check(only_from) representation.
/// Carefully tested to be maximally compatible with legacy
/// integrations tests.
/// On error returns empty string
std::string AddressToCheckMkString(std::string_view entry);

class CheckMk final : public Synchronous {
public:
    explicit CheckMk() : Synchronous(section::kCheckMk) {}
    CheckMk(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    std::string makeBody() override;
    static std::string makeOnlyFrom();
};

std::string GetTimezoneOffset(
    std::chrono::time_point<std::chrono::system_clock> tp);

std::string PrintIsoTime(
    std::chrono::time_point<std::chrono::system_clock> now);
}  // namespace cma::provider

#endif  // CHECK_MK_H
