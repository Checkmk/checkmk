// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// Partial and not so valid support for string_view in YAML CPP
// No C++ file
#pragma once

#include <yaml-cpp/yaml.h>

#include <string>
#include <string_view>

namespace YAML {
template <>
inline const Node Node::operator[](
    const std::string_view &key) const {  // NOLINT
    return operator[](std::string(key));
}

template <>
inline Node Node::operator[](const std::string_view &key) {
    //
    return operator[](std::string(key));
}

template <>
inline bool Node::remove(const std::string_view &key) {
    //
    return remove(std::string(key));
}

}  // namespace YAML
