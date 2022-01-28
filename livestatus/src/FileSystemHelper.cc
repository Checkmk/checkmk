// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "FileSystemHelper.h"

#include <algorithm>
#include <system_error>
#include <utility>

namespace fs = std::filesystem;

namespace mk {

[[nodiscard]] std::string unescape_filename(const std::string &filename) {
    std::string filename_native;
    bool quote_active = false;
    for (auto c : filename) {
        if (quote_active) {
            if (c == 's') {
                filename_native += ' ';
            } else {
                filename_native += c;
            }
            quote_active = false;
        } else if (c == '\\') {
            quote_active = true;
        } else {
            filename_native += c;
        }
    }
    return fs::path{filename_native};
}

bool path_contains(const fs::path &directory, const fs::path &path) {
    std::error_code ec{};
    const fs::path can_dir{fs::canonical(directory, ec)};
    if (ec) {
        return false;
    }
    const fs::path can_path{fs::canonical(path, ec)};
    if (ec) {
        return false;
    }
    auto pair = std::mismatch(can_dir.begin(), can_dir.end(), can_path.begin(),
                              can_path.end());
    return pair.first == can_dir.end();
}

}  // namespace mk
