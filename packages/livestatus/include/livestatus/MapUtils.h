// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef MapUtils_h
#define MapUtils_h

#include <algorithm>
#include <iterator>
#include <vector>

namespace mk {
template <typename T>
std::vector<typename T::key_type> map_keys(const T &map) {
    std::vector<typename T::key_type> out;
    out.reserve(map.size());
    std::transform(
        std::begin(map), std::end(map), std::back_inserter(out),
        [](const typename T::value_type &pair) { return pair.first; });
    return out;
}

template <typename T>
std::vector<typename T::mapped_type> map_values(const T &map) {
    std::vector<typename T::mapped_type> out;
    out.reserve(map.size());
    std::transform(
        std::begin(map), std::end(map), std::back_inserter(out),
        [](const typename T::value_type &pair) { return pair.second; });
    return out;
}
}  // namespace mk

#endif
