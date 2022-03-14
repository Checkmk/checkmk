// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef LogwatchListColumn_h
#define LogwatchListColumn_h

#include "config.h"  // IWYU pragma: keep

#include <filesystem>
#include <string>
#include <vector>

class Column;

[[nodiscard]] std::vector<std::string> getLogwatchList(
    const std::filesystem::path &dir, const Column &col);

#endif  // LogwatchListColumn_h
