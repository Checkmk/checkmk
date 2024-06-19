// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Sorter_h
#define Sorter_h

#include <chrono>
#include <optional>
#include <string>
#include <variant>

class RowRenderer;
class Row;
class User;

class Sorter {
public:
    using key_type = std::variant<std::string, double, int,
                                  std::chrono::system_clock::time_point>;
    Sorter() = default;
    virtual ~Sorter() = default;
    [[nodiscard]] virtual key_type getKey(
        Row, const std::optional<std::string> &key, const User &user,
        std::chrono::seconds timezone_offset) const = 0;
};

#endif
