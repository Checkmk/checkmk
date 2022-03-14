// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "LogwatchList.h"

#include <algorithm>
#include <iterator>

#include "Column.h"
#include "Logger.h"

std::vector<std::string> getLogwatchList(const std::filesystem::path &dir,
                                         const Column &col) {
    if (dir.empty()) {
        return {};
    }
    try {
        if (std::filesystem::exists(dir)) {
            std::vector<std::string> filenames;
            auto it = std::filesystem::directory_iterator(dir);
            std::transform(begin(it), end(it), std::back_inserter(filenames),
                           [](const auto &entry) {
                               return entry.path().filename().string();
                           });
            return filenames;
        }
    } catch (const std::filesystem::filesystem_error &e) {
        Warning(col.logger()) << col.name() << ": " << e.what();
    }
    return {};
}
