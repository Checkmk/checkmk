// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "FileSystemHelper.h"
#include <algorithm>
#include <filesystem>
#include <system_error>
#include <utility>

namespace fs = std::filesystem;

[[nodiscard]] std::string mk::unescape_filename(const std::string& filename) {
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

bool mk::path_contains(const fs::path& directory, const fs::path& path) {
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
