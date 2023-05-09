// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "RRDColumn.h"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <type_traits>

namespace detail {
bool isVariableName(const std::string &token) {
    auto is_operator = [](char c) { return strchr("+-/*", c) != nullptr; };
    auto is_number_part = [](char c) {
        return strchr("0123456789.", c) != nullptr;
    };

    return !(is_operator(token[0]) ||
             std::all_of(token.begin(), token.end(), is_number_part));
}

// TODO(sp): copy-n-paste from pnp4nagios.cc
std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}

std::pair<Metric::Name, std::string> getVarAndCF(const std::string &str) {
    size_t dot_pos = str.find_last_of('.');
    if (dot_pos != std::string::npos) {
        Metric::Name head{str.substr(0, dot_pos)};
        std::string tail = str.substr(dot_pos);
        if (tail == ".max") {
            return std::make_pair(head, "MAX");
        }
        if (tail == ".min") {
            return std::make_pair(head, "MIN");
        }
        if (tail == ".average") {
            return std::make_pair(head, "AVERAGE");
        }
    }
    return std::make_pair(Metric::Name{str}, "MAX");
}
};  // namespace detail
