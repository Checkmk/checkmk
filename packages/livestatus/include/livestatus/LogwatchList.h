// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogwatchList_h
#define LogwatchList_h

#include <filesystem>
#include <string>
#include <vector>

class Column;

[[nodiscard]] std::vector<std::string> getLogwatchList(
    const std::filesystem::path &dir, const Column &col);

#endif  // LogwatchList_h
